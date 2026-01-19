from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from prompts import *
from logger import get_logger
from utils import *
import logging
import os
import re
import json
from deepdiff import DeepDiff
from memory_manager.skeleton_memory import get_session_history
from generation_schema import SKELETON_JSON_SCHEMA
from prompt_templates.skeleton_prompts import SkeletonPrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from typing import Tuple, Dict, Any, Optional, List


class SkeletonAgent:

    def __init__(self, llm):
        self.base_llm = llm
        self.model = self.base_llm.with_structured_output(SKELETON_JSON_SCHEMA, method="json_schema")
        self.clean_history_runnable = RunnableLambda(clean_history)
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.skeleton_json_dir_suffix = "/tmp_files"

    def get_session_id(self, repo_name: str) -> str:
        return f"skeleton_agent_{repo_name}"

    def init_skeleton_chain(self, input_key: str) -> RunnableWithMessageHistory:
        prompt = SkeletonPrompts.init_prompt()
        skeleton_chain = RunnableWithMessageHistory(
            prompt | self.model,
            get_session_history=get_session_history,
            input_messages_key=input_key,
            history_messages_key="history"
        )
        return skeleton_chain

    def iter_skeleton_chain(self, input_key: str) -> RunnableWithMessageHistory:
        prompt = SkeletonPrompts.iter_prompt()
        skeleton_iter_chain = RunnableWithMessageHistory(
            self.clean_history_runnable | prompt | self.model,
            get_session_history=get_session_history,
            input_messages_key=input_key,
            history_messages_key="history"
        )
        return skeleton_iter_chain

    def process_file_skeleton(self, chain, input_data: Dict[str, Any], session_id: str, steps: int, feedback: str = "") -> Optional[Dict[str, Any]]:
        try:
            self.logger.info(f"[Skeleton Agent] Processing file: {input_data['file_item']['path']}")
            config = {
                "configurable": {"session_id": session_id, "agent": "skeleton_agent", "step": steps},
                "callbacks": [self.metrics_handler]
            }
            # 迭代步骤添加feedback到config
            if feedback:
                config["configurable"]["feedback"] = feedback
            
            result = chain.invoke(input_data, config=config)
            return result
        except Exception as e:
            self.logger.error(f"[Skeleton Agent] Error in step {steps} when generating skeleton for file {input_data['file_item'].get('path', '')}: {e}")
            # TODO: 增加错误处理，当无法正常生成时不要直接跳过，继续重新生成
            return None

    def generate_first_skeleton(self, latest_arch: Dict[str, Any], session_id: str, steps: int) -> List[Dict[str, Any]]:
        # TODO: context怎么给？
        context = []
        input_key = "latest_arch"
        skeleton_chain = self.init_skeleton_chain(input_key)

        # 原先：先将ssat中的所有file都收集在一个list中，然后逐个生成
        # 现在：按照module顺序，依次处理每个module下的file，保持一定的上下文连续性
        for module in latest_arch.get("modules", []):
            files = module.get("files", [])
            for file_item in files:
                input_data = {
                    "file_item": file_item,
                    "context": context,
                    "step": steps
                }
                result = self.process_file_skeleton(skeleton_chain, input_data, session_id, steps)
                if result:
                    file_item["skeleton_code"] = result["skeleton_code"]
                    context.append(result)
                else:
                    file_item["skeleton_code"] = ""

        memory = get_session_history(session_id)
        memory.save_context({"step": steps}, {"result": context})

        return context

    def generate_iter_skeleton(self, latest_arch: Dict[str, Any], latest_skeleton: List[Dict[str, Any]], feedback: str, session_id: str, steps: int) -> Tuple[List[Dict[str, Any]], str]:
        context: List[Dict[str, Any]] = []
        input_key = "latest_arch"
        skeleton_iter_chain = self.iter_skeleton_chain(input_key)

        memory = get_session_history(session_id)
        history_str = memory.load_memory_variables({"feedback": feedback})["history"]

        for module in latest_arch.get("modules", []):
            files = module.get("files", [])
            for file_item in files:
                input_data = {
                    "previous_skeleton": latest_skeleton,
                    "file_item": file_item,
                    "context": context,
                    "feedback": feedback,
                    "step": steps,
                    "history_str": history_str
                }
                result = self.process_file_skeleton(skeleton_iter_chain, input_data, session_id, steps, feedback)
                if result:
                    file_item["skeleton_code"] = result["skeleton_code"]
                    context.append(result)
                else:
                    file_item["skeleton_code"] = ""

        skeleton_diff = ""
        if context:
            skeleton_diff = json.dumps(DeepDiff(latest_skeleton, context, ignore_order=True), indent=2, default=str)

        memory.save_context(
            {"step": steps, "previous_skeleton": latest_skeleton, "feedback": feedback},
            {"result": context, "skeleton_diff": skeleton_diff}
        )

        return context, skeleton_diff

    def save_skeleton_json(self, repo_dir: str, steps: int, context: list) -> None:
        skeleton_json_dir = f"{repo_dir}{self.skeleton_json_dir_suffix}"
        # 确保目录存在
        os.makedirs(skeleton_json_dir, exist_ok=True)
        skeleton_json_path = f"{skeleton_json_dir}/skeleton_{steps}.json"

        try:
            with open(skeleton_json_path, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2, ensure_ascii=False)
            self.logger.info(f"[Skeleton Agent] Skeleton JSON saved to {skeleton_json_path}")
        except Exception as e:
            self.logger.error(f"[Skeleton Agent] Could not save skeleton JSON to file: {e}")

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        code_file_DAG = state["code_file_DAG"]
        latest_arch = state["latest_arch"]
        latest_skeleton = state.get("latest_skeleton", [])
        steps = state.get("skeleton_steps", 0) + 1
        feedback = state.get("skeleton_feedback", "")
        session_id = self.get_session_id(repo_name)

        self.logger.info(f"==========SKELETON GENERATION IN STEP {steps}===========")

        if steps == 1:
            skeleton = self.generate_first_skeleton(latest_arch, session_id, steps)
        else:
            skeleton, _ = self.generate_iter_skeleton(latest_arch, latest_skeleton, feedback, session_id, steps)

        self.save_skeleton_json(repo_dir, steps, skeleton)

        updated_state = {
            **state,
            "repo_name": repo_name,
            "repo_dir": repo_dir,
            "code_file_DAG": code_file_DAG,
            "latest_arch": latest_arch,
            "latest_skeleton": skeleton,
            "skeleton_steps": steps,
            "dataset": dataset
        }
        return updated_state
