from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from prompts import *
from logger import get_logger
import os
import json
import subprocess
from agents.test import Test
from utils import *
from json_repair import repair_json
from generation_schema import CODE_JUDGE_SCHEMA, EXPERIENCE_JSON_SCHEMA
from prompt_templates.code_judge_prompts import CodeJudgePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from memory_manager.code_shared_memory import update_step, SharedStepRecord, load_step, append_experience, Experience
from datetime import datetime


class CodeJudgeAgent:
    MAX_CODE_ITER = 5
    TEST_BASE_DIR = "/home/zhaoqianhui/workspace/new-projectgen/datasets/"

    def __init__(self, llm, secondery_llm):
        self.base_llm = llm
        self.model = llm.with_structured_output(CODE_JUDGE_SCHEMA, method="json_schema")
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.secondery_llm = secondery_llm.with_structured_output(EXPERIENCE_JSON_SCHEMA, method="json_schema")

    def get_session_id(self, repo_name: str) -> str:
        return f"code_judge_agent_{repo_name}"

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        return ChatMessageHistory()

    def write_code_to_files(self, latest_code: any, repo_dir: str) -> tuple[bool, list]:
        written_files = []
        if isinstance(latest_code, str):
            try:
                code_data = json.loads(latest_code)
            except Exception as e:
                self.logger.error(f"Code JSON parsing failed: {e}")
                return False, []
        else:
            code_data = latest_code

        for item in code_data:
            file_path = os.path.join(repo_dir, item["path"])
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(item["code"])
                written_files.append(file_path)
            except Exception as e:
                self.logger.error(f"Error writing file {file_path}: {e}")

        return True, written_files

    def remove_written_files(self, written_files: list) -> None:
        for f in written_files:
            try:
                os.remove(f)
                self.logger.debug(f"Removed temporary file: {f}")
            except Exception as e:
                self.logger.warning(f"Failed to remove file {f}: {e}")

    def run_pytest_and_collect(self, dataset: str, repo_name: str, repo_dir: str) -> tuple[str, int, int]:
        test_dir = f"{self.TEST_BASE_DIR}{dataset}/{repo_name}"
        t = Test(test_dir, repo_dir, logger=self.logger)
        # TODO: 改成相对路径有bug？
        test_output, error, passed, total = t.test(repo_dir, "python")
        return test_output, error, passed, total

    def generate_test_feedback(self, test_output: str, error: bool, passed: int, total: int, result: dict = None) -> str:
        if passed == total and total > 0:
            return "All unit tests passed.\n"
        else:
            if error:
                feedback = "Test cases failed to run as expected because of errors in the code.\n"
            else:
                feedback = f"Code failed the unit tests. Only pass {passed} out of {total} test cases.\n"
            if result:
                feedback += "\nHere are some suggestions:\n\n"
                feedback += json.dumps(result, indent=2, ensure_ascii=False)
            return feedback

    def run_code_judge_chain(self, test_output: str, session_id: str, steps: int) -> dict:
        prompt = CodeJudgePrompts.get_prompt()
        input_key = "error_log"
        input_data = {
            "error_log": test_output
        }

        judge_code_chain = RunnableWithMessageHistory(
            prompt | self.model,
            get_session_history=self.get_session_history,
            input_messages_key=input_key,
            history_messages_key="history",
        )

        try:
            result = judge_code_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": session_id, "agent": "code_judge_agent", "step": steps},
                    "callbacks": [self.metrics_handler]
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"[Code Judge Agent] Error in step {steps}: {e}")
            raise e  # 抛出异常供上层处理

    def make_judge_decision(self, passed: int, total: int, steps: int, written_files: List) -> tuple[bool, str]:
        if passed == total and total > 0:
            return True, ""
        
        if steps >= self.MAX_CODE_ITER:
            return True, "Maximum CODE iterations reached, forcing approval.\n"
        
        self.remove_written_files(written_files)
        
        return False, ""
    
    # 得到上轮代码测试的结果
    def get_previous_test_result(self, repo_name: str, steps: int) -> tuple[int, int]:
        shared_session_id = f"code_shared_{repo_name}"
        load = None
        if steps > 1:
            try:
                load = load_step(shared_session_id, step=steps)
            except Exception:
                load = None

        if load is not None:
            if getattr(load, "test_result", None):
                tr = load.test_result
                if tr.get("error") is False:
                    prev_passed = tr.get("passed")
                else:
                    prev_passed = -1
            else:
                prev_passed = -1
        return prev_passed

    # # 判断新的代码是否比上轮代码的测试结果好，如果是则继续流程，否则将代码回退至上次的版本 并总结经验存入记忆 并告诉llm不能这样修改
    # # 这里只处理不能通过所有check test的分支，只处理steps>1的情况
    # # 返回值：是否需要回退（同时在本步完成经验的更新）
    # def check_code_improvement(self, repo_name: str, passed: int, total: int, steps: int, written_files: List) -> tuple[bool, str]:
    #     prev_passed = self.get_previous_test_result(repo_name, steps)
    #     # 比较这次和上次通过的结果
    #     if passed > prev_passed:
    #         # 总结这次修改的经验
    #         self.update_experience()
    #     elif passed == prev_passed:
    #         # TODO: 看这次的报错是否和上次一样，如果不一样总结成功的那部分经验，如果一样总结为什么这样修改不对
    #         pass
    #     else:
    #         # 总结改不对的经验，同时回退到上一个版本
    #         self.update_experience()
    #         self.code_undo()
    #         pass

    # def check_code_improvement(self, repo_name: str, passed: int, total: int, steps: int, written_files: List) -> tuple[bool, str]:
    #     prev_passed = self.get_previous_test_result(repo_name, steps)
    #     # 比较这次和上次通过的结果
    #     if passed > prev_passed:
    #         return True, "improved"
    #     elif passed == prev_passed:
    #         return False, "same"
    #     else:
    #         return False, "worse"

    # # code回退到上一个版本
    # def code_undo():
    #     pass

    # 更新经验池，包括成功的和失败的
    def update_experience(self, repo_name: str, steps: int, passed: int, total: int, test_output: str, result: dict, repo_dir: str) -> None:
        """Call secondary LLM to summarize experience and persist to shared memory (step-level and repo-level).

        The generated experience should be a JSON-like dict matching Experience dataclass.
        """
        self.logger.info(f"[Code Judge Agent] Summarizing experience for step {steps}... (in)")
        try:
            shared_session_id = f"code_shared_{repo_name}"
            prev = load_step(shared_session_id, step=steps - 1)
            curr = load_step(shared_session_id, step=steps)

            # safely extract feedback text (feedbacks may be missing or not a dict)
            prev_fb_obj = getattr(prev, "feedbacks", None)
            if isinstance(prev_fb_obj, dict):
                prev_feedbacks = prev_fb_obj.get("text", "")
            else:
                prev_feedbacks = ""

            curr_fb_obj = getattr(curr, "feedbacks", None)
            if isinstance(curr_fb_obj, dict):
                curr_feedbacks = curr_fb_obj.get("text", "")
            else:
                curr_feedbacks = ""

            curr_code = getattr(curr, "generated_code", []) if curr else []
            
            # extract only files with non-empty diffs
            def extract_diffs(code_list):
                diffs = []
                for item in (code_list or []):
                    try:
                        d = item.get("diff") if isinstance(item, dict) else None
                    except Exception:
                        d = None
                    if d:
                        diffs.append({"path": item.get("path"), "diff": d})
                return diffs

            diffs = extract_diffs(curr_code)

            prev_passed = self.get_previous_test_result(repo_name, steps)
            curr_passed = passed

            prompt = CodeJudgePrompts.get_experience_prompt()
            input_data = {
                "prev_passed": prev_passed,
                "prev_feedback": prev_feedbacks,
                "curr_passed": curr_passed,
                "curr_feedback": curr_feedbacks,
                "diffs": diffs
            }
            input_key = "diffs"

            summary_chain = RunnableWithMessageHistory(
                prompt | self.secondery_llm,
                get_session_history=self.get_session_history,
                input_messages_key=input_key,
                history_messages_key="history",
            )

            # invoke the secondary LLM to summarize experiences
            result = summary_chain.invoke(
                input_data,
                config={"configurable": {"session_id": self.get_session_id(repo_name), "agent": "code_judge_agent", "step": steps}, "callbacks": [self.metrics_handler]}
            )
            experiences_list = result.get("experiences", [])
            # defensive checks and logging for debugging
            if experiences_list is None:
                self.logger.warning(f"[Code Judge Agent] summary_chain returned None for step {steps}")
                experiences_list = []
            else:
                self.logger.debug(f"[Code Judge Agent] summary_chain returned type {type(experiences_list)} with len={len(experiences_list) if hasattr(experiences_list, '__len__') else 'unknown'}")

            add_experienve_count = 0
            for exp_entry in experiences_list:
                # persist as Experience dataclass via append_experience
                try:
                    exp_obj = Experience(kind=exp_entry.get("kind", "failure"), scenario=exp_entry.get("scenario", ""), experience=exp_entry.get("experience", {}), step=steps)
                    append_experience(shared_session_id, steps, exp_obj, repo_dir=repo_dir)
                    add_experienve_count += 1
                except Exception:
                    # fallback: write raw dict into step experiences
                    try:
                        update_step(shared_session_id, steps, {"experiences": [exp_entry]}, repo_dir=repo_dir)
                        add_experienve_count += 1
                    except Exception:
                        pass
            self.logger.info(f"[Code Judge Agent] Generated {len(experiences_list)} experiences. Added {add_experienve_count} experiences for step {steps}.")
        except Exception as e:
            self.logger.exception(f"[Code Judge Agent] Failed to summarize/persist experiences for step {steps}: {e}")
            # propagate or return early to avoid silent failures
            return

    def load_current_step_code(self, repo_name: str, steps: int) -> tuple[list, str, str]:
        # load previous step data from shared memory
        shared_session_id = f"code_shared_{repo_name}"
        load = None
        generated_code = []
        if steps > 1:
            try:
                load = load_step(shared_session_id, step=steps)
            except Exception:
                load = None

        if load is not None:
            if getattr(load, "generated_code", []):
                generated_code = load.generated_code

        return generated_code
        

    def __call__(self, state: dict) -> dict:
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        # latest_code = state["latest_code"]
        steps = state["code_steps"]
        # test_status = state.get("test_status", {})
        session_id = self.get_session_id(repo_name)

        self.logger.info(f"==========CODE CHECK IN STEP {steps}===========")

        latest_code = self.load_current_step_code(repo_name, steps)

        write_ok, written_files = self.write_code_to_files(latest_code, repo_dir)
        feedback = ""
        if not write_ok:
            feedback = "Code JSON parsing failed."
            self.logger.info(f"[decision]: False")
            self.logger.info(f"[feedback]: {feedback}")
            self.remove_written_files(written_files)
            
            code_decision = False
            test_output = ""
            passed, total = 0, 0
            error = True
            test_status = "test cases fail to run as expected because of Code JSON parsing failure"

        else:
            test_output, error, passed, total = self.run_pytest_and_collect(dataset, repo_name, repo_dir)
            if error:
                test_status = "test cases fail to run as expected because of errors"
            else:
                test_status = f"passed {passed} out of {total}"
            code_decision, force_feedback = self.make_judge_decision(passed, total, steps, written_files)

        # write test result into shared step record
        try:
            shared_session_id = f"code_shared_{repo_name}"
            test_result = {
                "passed": passed,
                "total": total,
                "error": error,
                "output": test_output,
                "test_status" : test_status
            }
            update_step(shared_session_id, steps, {"test_result": test_result}, repo_dir=repo_dir)
        except Exception:
            pass

        
        if code_decision and force_feedback == "":
            feedback = self.generate_test_feedback(test_output, error, passed, total)
            result = None
        elif code_decision is False and feedback == "Code JSON parsing failed.":
            result = None
        else:
            try:
                result = self.run_code_judge_chain(test_output, session_id, steps)
                feedback = self.generate_test_feedback(test_output, error, passed, total, result)
                feedback = force_feedback + feedback
            except Exception as e:
                # TODO: 错误处理
                self.logger.error(f"[Code Judge Agent] Error in step {steps}: {e}")
                feedback = "Code judge agent encountered an error."
                code_decision = False
                self.logger.info(f"[decision]: False")
                self.logger.info(f"[feedback]: {feedback}")
                result = None

        # Persist structured feedback (including raw `result`) into shared memory
        try:
            shared_session_id = f"code_shared_{repo_name}"
            fb = {
                "result": result if result is not None else [],
                "text": feedback
            }
            update_step(shared_session_id, steps, {"feedbacks": fb}, repo_dir=repo_dir)
        except Exception:
            pass

        # 调试信息：记录决策与步数以便排查为何未进入经验生成分支
        self.logger.info(f"[Code Judge Agent] Decision debug: code_decision={code_decision}, steps={steps}, passed={passed}, total={total}, force_feedback={locals().get('force_feedback', None)}")

        # 总结经验
        # If failed and not first step, summarize experience via secondary LLM and persist
        if code_decision is False and steps > 1:
            try:
                self.logger.info(f"[Code Judge Agent] Summarizing experience for step {steps}...")
                self.update_experience(repo_name, steps, passed, total, test_output, result, repo_dir)
            except Exception:
                pass

        self.logger.info(f"[decision]: {code_decision}")
        self.logger.info(f"[feedback]: {feedback}")


        updated_state = {
            **state,
            "code_decision": code_decision,
            "code_feedback": feedback,
            "test_status": test_status,
            "code_steps": steps,
            "dataset": dataset
        }
        return updated_state