from langchain.chains import LLMChain
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
from json_repair import repair_json
from deepdiff import DeepDiff
from memory_manager.arch_memory import get_session_history
from generation_schema import SSAT_JSON_SCHEMA
from prompt_templates.architecture_prompts import ArchitecturePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from typing import Tuple, Dict, Any, Optional


class ArchitectureAgent:

    def __init__(self, llm):
        self.base_llm = llm
        self.model = self.base_llm.with_structured_output(SSAT_JSON_SCHEMA, method="json_schema")
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler() 
        self.arch_json_dir_suffix = "/tmp_files"

    def get_session_id(self, repo_name: str) -> str:
        return f"architecture_agent_{repo_name}"

    def prepare_prompt_and_input(self, state: Dict[str, Any]) -> Tuple[PromptTemplate, str, Dict[str, Any]]:
        steps = state.get("arch_steps", 0) + 1
        prd = state["user_input"]
        uml_class = state["uml_class"]
        uml_sequence = state["uml_sequence"]
        arch_design = state["arch_design"]

        # 首次迭代 vs 后续迭代的prompt区分
        if steps == 1:
            prompt = ArchitecturePrompts.init_prompt()
            input_key = "prd"
            input_data = {
                "prd": prd,
                "uml_class": uml_class,
                "uml_sequence": uml_sequence,
                "arch_design": arch_design,
                "step": steps
            }
        else:
            prompt = ArchitecturePrompts.iter_prompt()
            input_key = "latest_arch"
            input_data = {
                "prd": prd,
                "uml_class": uml_class,
                "uml_sequence": uml_sequence,
                "arch_design": arch_design,
                "latest_arch": state.get("latest_arch", ""),
                "feedback": state.get("arch_feedback", ""),
                "step": steps
            }
        return prompt, input_key, input_data

    def compute_arch_diff(self, latest_arch: Dict[str, Any], new_arch: Dict[str, Any]) -> Optional[str]:
        try:
            arch_diff = json.dumps(DeepDiff(latest_arch, new_arch, ignore_order=True), indent=2, default=str)
            self.logger.info(f"Architecture diff:\n{arch_diff}")
            return arch_diff
        except Exception as e:
            self.logger.warning(f"[Architecture Agent] Could not compute architecture diff: {e}")
            return None

    def save_arch_json(self, repo_dir: str, steps: int, arch_data: dict) -> None:
        arch_json_dir = f"{repo_dir}{self.arch_json_dir_suffix}"
        # 确保目录存在
        os.makedirs(arch_json_dir, exist_ok=True)
        arch_json_path = f"{arch_json_dir}/architecture_{steps}.json"
        
        try:
            with open(arch_json_path, "w", encoding="utf-8") as f:
                json.dump(arch_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"[Architecture Agent] Architecture JSON saved to {arch_json_path}")
        except Exception as e:
            self.logger.error(f"[Architecture Agent] Could not save architecture JSON to file: {e}")

    def run_architecture_chain(self, prompt: PromptTemplate, input_key: str, input_data: Dict[str, Any], session_id: str, steps: int, feedback: str) -> Dict[str, Any]:
        architecture_chain = RunnableWithMessageHistory(
            prompt | self.model,
            get_session_history=get_session_history,
            input_messages_key=input_key,
            history_messages_key="history"
        )

        # 执行chain
        try:
            result = architecture_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": session_id, "agent": "architecture_agent", "step": steps, "feedback": feedback},
                    "callbacks": [self.metrics_handler]
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"[Architecture Agent] Error in step {steps}: {e}")
            raise e
        
    def update_memory(self, session_id: str, steps: int, input_data: Dict[str, Any], latest_arch: Dict[str, Any], result: Dict[str, Any]) -> None:
        memory = get_session_history(session_id)
        if steps > 1:
            arch_diff = self.compute_arch_diff(latest_arch, result)
            memory.save_context(input_data, {"result": result, "arch_diff": arch_diff})
            self.logger.info(f"[Architecture Agent] Memory updated with diff (step {steps})")
        else:
            memory.save_context(input_data, {"result": result})
            self.logger.info(f"[Architecture Agent] Initial memory saved (step {steps})")

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        prd = state["user_input"]
        uml_class = state["uml_class"]
        uml_sequence = state["uml_sequence"]
        arch_design = state["arch_design"]
        code_file_DAG = state["code_file_DAG"]
        steps = state.get("arch_steps", 0) + 1
        latest_arch = state.get("latest_arch", "")
        feedback = state.get("arch_feedback", "")

        self.logger.info(f"==========ARCHITECTURE GENERATION IN STEP {steps}===========")
        prompt, input_key, input_data = self.prepare_prompt_and_input(state)
        session_id = self.get_session_id(repo_name)

        result = self.run_architecture_chain(prompt, input_key, input_data, session_id, steps, feedback)

        self.update_memory(
            session_id=session_id,
            steps=steps,
            input_data=input_data,
            latest_arch=latest_arch,
            result=result
        )

        self.save_arch_json(repo_dir, steps, result)

        updated_state = {
            **state,
            "repo_name": repo_name,
            "repo_dir": repo_dir,
            "requirement": prd,
            "uml_class": uml_class,
            "uml_sequence": uml_sequence,
            "arch_design": arch_design,
            "code_file_DAG": code_file_DAG,
            "latest_arch": result,
            "arch_steps": steps,
            "dataset": dataset
        }
        return updated_state