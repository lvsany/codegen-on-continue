from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from prompts import *
import os
from logger import get_logger
from utils import *
import logging
import re
import py_compile
from generation_schema import SKELETON_JUDGE_SCHEMA
from prompt_templates.skeleton_judge_prompt import SkeletonJudgePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler

class SkeletonJudgeAgent:
    MAX_SKELETON_ITER = 3
    PASS_SCORE = 8 

    def __init__(self, llm):
        self.base_llm = llm
        self.model = self.base_llm.with_structured_output(SKELETON_JUDGE_SCHEMA, method="json_schema")
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()

    def get_session_id(self, repo_name: str) -> str:
        return f"skeleton_judge_agent_{repo_name}"

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        return ChatMessageHistory()

    def write_skeleton_to_files(self, latest_skeleton: any, repo_dir: str) -> tuple[bool, list]:
        written_files = []
        if isinstance(latest_skeleton, str):
            try:
                skeleton_data = json.loads(latest_skeleton)
            except Exception as e:
                self.logger.error(f"[Skeleton Judge Agent] Skeleton JSON parsing failed: {e}")
                return False, []
        else:
            skeleton_data = latest_skeleton

        for item in skeleton_data:
            file_path = os.path.join(repo_dir, item["path"])
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(item["skeleton_code"])
                written_files.append(file_path)
            except Exception as e:
                self.logger.error(f"[Skeleton Judge Agent] Error writing file {file_path}: {e}")

        return True, written_files

    def remove_written_files(self, written_files: list) -> None:
        for f in written_files:
            try:
                os.remove(f)
                self.logger.debug(f"Removed temporary file: {f}")
            except Exception as e:
                self.logger.warning(f"[Skeleton Judge Agent] Failed to remove file {f}: {e}")

    def check_python_compile(self, repo_dir: str) -> tuple[bool, list]:
        error_msgs = []
        all_pass = True
        for root, dirs, files in os.walk(repo_dir):
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    try:
                        py_compile.compile(fpath, doraise=True)
                    except py_compile.PyCompileError as e:
                        all_pass = False
                        error_msgs.append(f"{fpath}:\n{e.msg}")
                        self.logger.error(f"Python compile error in {fpath}: {e.msg}")
        return all_pass, error_msgs

    def run_skeleton_judge_chain(self, input_data: dict, session_id: str, steps: int) -> dict:
        prompt = SkeletonJudgePrompts.get_prompt()
        input_key = "skeleton"

        judge_skeleton_chain = RunnableWithMessageHistory(
            prompt | self.model,
            get_session_history=self.get_session_history,
            input_messages_key=input_key,
            history_messages_key="history",
        )

        try:
            result = judge_skeleton_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": session_id, "agent": "skeleton_judge_agent", "step": steps},
                    "callbacks": [self.metrics_handler]
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"[Skeleton Judge Agent] Error in step {steps}: {e}")
            raise e 

    def generate_judge_feedback(self, result: dict) -> str:
        feed_back = f"Final Score: {result['final_score']}\n"
        feed_back += "\n".join([f"{k}: {v}" for k, v in result["feedback"].items()])
        return feed_back

    def make_judge_decision(self, result: dict, steps: int, feed_back: str) -> tuple[bool, str]:
        decision = result["final_score"] >= self.PASS_SCORE

        if steps >= self.MAX_SKELETON_ITER:
            decision = True
            feed_back = "Maximum skeleton iterations reached, forcing approval.\n" + feed_back
            self.logger.warning(f"Max skeleton iterations ({self.MAX_SKELETON_ITER}) reached, forcing approval")

        return decision, feed_back

    def __call__(self, state: dict) -> dict:
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        code_file_DAG = state["code_file_DAG"]
        repo_dir = state["repo_dir"]
        latest_arch = state["latest_arch"]
        latest_skeleton = state["latest_skeleton"]
        steps = state["skeleton_steps"]
        session_id = self.get_session_id(repo_name)

        self.logger.info(f"==========SKELETON CHECK IN STEP {steps}===========")

        write_ok, written_files = self.write_skeleton_to_files(latest_skeleton, repo_dir)
        if not write_ok:
            feed_back = "Skeleton JSON parsing failed."
            self.logger.info(f"[decision]: False")
            self.logger.info(f"[feedback]: {feed_back}")
            return {
                **state,
                "repo_name": repo_name,
                "repo_dir": repo_dir,
                "code_file_DAG": code_file_DAG,
                "skeleton_decision": False,
                "skeleton_feedback": feed_back,
                "latest_skeleton": latest_skeleton,
                "skeleton_steps": steps,
                "dataset": dataset
            }

        compile_ok, compile_errors = self.check_python_compile(repo_dir)
        self.remove_written_files(written_files)
        if not compile_ok:
            feed_back = "Skeleton failed the Python compilation check. Please correct the syntax error.\n"
            feed_back += "\n".join(compile_errors)
            self.logger.info(f"[decision]: False")
            self.logger.info(f"[feedback]: {feed_back}")
            return {
                **state,
                "repo_name": repo_name,
                "repo_dir": repo_dir,
                "code_file_DAG": code_file_DAG,
                "skeleton_decision": False,
                "skeleton_feedback": feed_back,
                "latest_skeleton": latest_skeleton,
                "skeleton_steps": steps,
                "dataset": dataset
            }

        input_data = {
            "skeleton": latest_skeleton,
            "architecture": latest_arch
        }
        result = self.run_skeleton_judge_chain(input_data, session_id, steps)
        feed_back = self.generate_judge_feedback(result)
        decision, feed_back = self.make_judge_decision(result, steps, feed_back)

        self.logger.info(f"[decision]: {decision}")
        self.logger.info(f"[feedback]: {feed_back}")

        updated_state = {
            **state,
            "repo_name": repo_name,
            "repo_dir": repo_dir,
            "code_file_DAG": code_file_DAG,
            "skeleton_decision": decision,
            "skeleton_feedback": feed_back,
            "latest_skeleton": latest_skeleton,
            "skeleton_steps": steps,
            "dataset": dataset
        }
        return updated_state