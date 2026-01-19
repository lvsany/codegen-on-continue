from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from prompts import *
import os
from logger import get_logger
from utils import *
import logging
import re
from generation_schema import ARCH_JUDGE_JSON_SCHEMA
from prompt_templates.arch_judge_prompts import ArchJudgePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler


class ArchJudgeAgent:
    MAX_ARCH_ITER = 3
    PASS_SCORE = 8  # 架构通过的最低分数（可外部覆盖）

    def __init__(self, llm):
        self.base_llm = llm
        self.model = self.base_llm.with_structured_output(ARCH_JUDGE_JSON_SCHEMA, method="json_schema")
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()

    def get_session_id(self, repo_name: str) -> str:
        return f"arch_judge_agent_{repo_name}"

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        return ChatMessageHistory()

    def validate_latest_arch(self, latest_arch: any) -> tuple[bool, str]:
        if latest_arch is None or latest_arch == "":
            return False, "No valid architecture generated in the previous step. Please ensure the output is strictly valid JSON."
        return True, ""

    def prepare_prompt_and_input(self, state: dict) -> tuple[PromptTemplate, str, dict]:
        prompt = ArchJudgePrompts.get_prompt()
        input_key = "architecture"
        input_data = {
            "requirement": state["requirement"],
            "uml_class": state["uml_class"],
            "uml_sequence": state["uml_sequence"],
            "arch_design": state["arch_design"],
            "architecture": state["latest_arch"]
        }
        return prompt, input_key, input_data

    def run_arch_judge_chain(self, prompt: PromptTemplate, input_key: str, input_data: dict, session_id: str, steps: int) -> dict:
        judge_arch_chain = RunnableWithMessageHistory(
            prompt | self.model,
            get_session_history=self.get_session_history,
            input_messages_key=input_key,
            history_messages_key="history",
        )

        try:
            result = judge_arch_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": session_id, "agent": "arch_judge_agent", "step": steps},
                    "callbacks": [self.metrics_handler]
                }
            )
            return result
        except Exception as e:
            # TODO: 可能出现哪些情况导致错误？遇到错误应该如何处理
            self.logger.error(f"[Architecture Judge Agent] Error in step {steps}: {e}")
            raise e  

    def generate_judge_feedback(self, result: dict) -> str:
        # TODO: 是返回str还是json更好？
        feed_back = f"Final Score: {result['final_score']}\n"
        feed_back += "\n".join([f"- {k.upper()}: {v}" for k, v in result["feedback"].items()])
        return feed_back

    def make_judge_decision(self, result: dict, steps: int, feed_back: str) -> tuple[bool, str]:
        # 分数是否达标
        decision = result["final_score"] >= self.PASS_SCORE

        # 强制通过：达到最大迭代次数
        if steps >= self.MAX_ARCH_ITER:
            decision = True
            feed_back = "Maximum architecture iterations reached, forcing approval.\n" + feed_back

        return decision, feed_back

    def __call__(self, state: dict) -> dict:
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        code_file_DAG = state["code_file_DAG"]
        repo_dir = state["repo_dir"]
        latest_arch = state["latest_arch"]
        requirement = state["requirement"]
        uml_class = state["uml_class"]
        uml_sequence = state["uml_sequence"]
        arch_design = state["arch_design"]
        steps = state["arch_steps"]
        session_id = self.get_session_id(repo_name)

        self.logger.info(f"==========ARCHITECTURE CHECK IN STEP {steps}===========")

        is_arch_valid, feed_back = self.validate_latest_arch(latest_arch)
        if not is_arch_valid:
            decision = False
        else:
            prompt, input_key, input_data = self.prepare_prompt_and_input(state)
            result = self.run_arch_judge_chain(prompt, input_key, input_data, session_id, steps)
            feed_back = self.generate_judge_feedback(result)
            decision, feed_back = self.make_judge_decision(result, steps, feed_back)

        self.logger.info(f"[decision]: {decision}")
        self.logger.info(f"[feedback]: {feed_back}")

        updated_state = {
            **state,
            "repo_name": repo_name,
            "repo_dir": repo_dir,
            "code_file_DAG": code_file_DAG,
            "arch_decision": decision,
            "arch_feedback": feed_back,
            "requirement": requirement,
            "latest_arch": latest_arch,
            "arch_steps": steps,
            "dataset": dataset
        }
        return updated_state
