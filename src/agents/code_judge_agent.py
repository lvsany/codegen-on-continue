from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain.tools import tool
from utils.logger import get_logger
import os
import json
import subprocess
from agents.test import Test
from utils.general_utils import *
from json_repair import repair_json
from typing import Tuple, Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from utils.generation_schema import CODE_JUDGE_SCHEMA, EXPERIENCE_JSON_SCHEMA
from utils.global_state import update_global_state, get_global_state, get_state_value
from prompt_templates.code_judge_prompts import CodeJudgePrompts, ExperiencePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from memory_manager.code_shared_memory import update_code_step, SharedStepCodeRecord, load_code_step, append_experience, Experience, load_best_generated_code
from datetime import datetime

class CodeFeedbackItem(BaseModel):
    summary: str = Field(description="A clear and concise summary of the issue found in the code.")
    likely_cause: str = Field(description="The most likely root cause of the issue found in the code.")
    suggested_fix: str = Field(description="The actionable modification suggestions to fix the issue.")

class CodeJudgeSchema(BaseModel):
    feedback: List[CodeFeedbackItem] = Field(description="A list of feedback items for the code evaluation.")

class Experience(BaseModel):
    kind: Literal["success", "failure"] = Field(description="The kind of experience.")
    scenario: str = Field(description="A short description of the error or success scenario.")
    experience: str = Field(description="The summarized coding experience.")

class ExperienceSummarySchema(BaseModel):
    experiences: List[Experience] = Field(description="A list of summarized coding experiences extracted from the interaction.")

@tool(description="Return the code of the given path.")
def find_code_of_file_by_path(path: str) -> dict:
    """Return the code of the given path."""
    code = get_state_value("code_by_path")
    if path in code.keys():
        return code[path]
    return None

def search_in_text(text: str, query: str) -> List[str]:
    """Return full sentences containing the query."""
    
    if not text or not query:
        return []

    SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[。！？.!?])\s+|\n+')
    sentences = SENTENCE_SPLIT_REGEX.split(text)
    results = []

    for sent in sentences:
        if re.search(re.escape(query), sent, flags=re.IGNORECASE):
            cleaned = sent.strip()
            if cleaned:
                results.append(cleaned)

    return results


@tool(description="Search relevant sections in PRD, UML, and Architecture Design documents by keyword.")
def search_docs_by_keyword(query: str, top_k: int = 5) -> str:
    """Search relevant sections in PRD, UML, and Architecture Design documents by keyword."""
    
    sources = {
        "PRD": get_state_value("prd"),
        "UML_Class": get_state_value("uml_class"),
        "UML_Sequence": get_state_value("uml_sequence"),
        "Arch_Design": get_state_value("arch_design"),
    }
    results = []

    for source_name, text in sources.items():
        if not text:
            continue
        matches = search_in_text(text, query)
        for m in matches:
            results.append({
                "source": source_name,
                "content": m.strip()
            })
    return {
        "query": query,
        "results": results[:top_k]
    }

class CodeJudgeAgent:
    MAX_CODE_ITER = 5
    TEST_BASE_DIR = "../datasets/"

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.code_json_dir_suffix = "/tmp_files"

        self.tools = [search_docs_by_keyword, find_code_of_file_by_path]

        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=CodeJudgePrompts.get_system_prompt(),
            response_format=ProviderStrategy(CodeJudgeSchema)
        ).with_config(callbacks=[self.metrics_handler])

        self.agent_chain_with_tools_for_experiences = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=ExperiencePrompts.get_system_prompt(),
            response_format=ProviderStrategy(ExperienceSummarySchema)
        ).with_config(callbacks=[self.metrics_handler])

    def write_code_to_files(self, code_data: any, repo_dir: str) -> tuple[bool, list]:
        written_files, error_files = [], []

        for item in code_data:
            file_path = os.path.join(repo_dir, item["path"])
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(item["code"])
                    self.logger.info(f"write {file_path}")
                written_files.append(file_path)
            except Exception as e:
                self.logger.error(f"[Code Judge Agent] Error writing file {file_path}: {e}")
                error_files.append(file_path)

        return written_files, error_files

    def remove_written_files(self, written_files: list) -> None:
        for f in written_files:
            try:
                os.remove(f)
                self.logger.info(f"[Code Judge Agent]: Successfully remove file {f}")
            except Exception as e:
                self.logger.warning(f"[Code Judge Agent] Failed to remove file {f}: {e}")

    def run_pytest_and_collect(self, dataset: str, repo_name: str, repo_dir: str) -> tuple[str, int, int]:
        test_dir = f"{self.TEST_BASE_DIR}{dataset}/{repo_name}"
        t = Test(test_dir, repo_dir, logger=self.logger)
        test_output, error, passed, total = t.test(repo_dir, "python")
        return test_output, error, passed, total

    def generate_test_feedback(self, error: bool, passed: int, total: int, result: list = None) -> str:
        if passed == total and total > 0:
            return "All unit tests passed.\n"
        else:
            if error:
                feedback = "Test cases failed to run as expected because of errors in the code.\n"
            else:
                feedback = f"Code failed the unit tests. Only pass {passed} out of {total} test cases.\n"
            if result:
                suggestion_text = "\nHere are some suggestions:\n\n"
                for item in result:
                    for k, v in item.items():
                        suggestion_text += f"{k}: {v}\n"
                        if k == 'suggested_fix':
                            suggestion_text += '\n'
                feedback += suggestion_text
            return feedback

    def run_code_judge_agent(self, test_output: str) -> dict:
        
        result = invoke_with_retry(
            self.agent_chain_with_tools,
            {
                "messages": CodeJudgePrompts.get_human_prompt().format_messages(
                    error_log=test_output
                )
            }
        )

        suggestions: CodeJudgeSchema = result["structured_response"]
        return suggestions.model_dump()["feedback"]

    def make_judge_decision(self, passed: int, total: int, steps: int, written_files: List) -> Dict:
        if passed == total and total > 0:
            return {"decision": "approve", "forced": False}
        
        if steps >= self.MAX_CODE_ITER:
            return {"decision": "approve", "forced": True}
        
        self.remove_written_files(written_files)
        
        return {"decision": "reject", "forced": False}

    def update_experience(self, repo_name: str, steps: int, passed: int, result: dict, repo_dir: str) -> None:
        
        shared_session_id = f"code_shared_{repo_name}"
        prev = load_code_step(shared_session_id, step=steps - 1)
        curr = load_code_step(shared_session_id, step=steps)

        prev_fb_obj = getattr(prev, "feedbacks", None)
        self.logger.info("get prev_fb_obj")
        prev_feedback_text = prev_fb_obj["text"] or ""
        self.logger.info("get prev_feedback_text")
        curr_fb_obj = getattr(curr, "feedbacks", None)
        curr_feedback_text = curr_fb_obj["text"] or ""

        diffs = getattr(curr, "diff_code", []) if curr else []

        diffs_text = ''
        for item in diffs:
            for k, v in item.items():
                diffs_text += f"{k}: {v}\n"
                if k == 'diff':
                    diffs_text += '\n'

        prev_passed = getattr(prev, "test_result", None).get("passed") or 0
        curr_passed = passed

        self.logger.info("start agent_chain_with_tools_for_experiences")
        result = invoke_with_retry(
            self.agent_chain_with_tools_for_experiences,
            {
                "messages": ExperiencePrompts.get_human_prompt().format_messages(
                    prev_passed=prev_passed,
                    prev_feedback=prev_feedback_text,
                    curr_passed=curr_passed,
                    curr_feedback=curr_feedback_text,
                    diffs=diffs_text
                )
            }
        )
        self.logger.info("end agent_chain_with_tools_for_experiences")
        experiences : ExperienceSummarySchema = result["structured_response"]
        experiences_list = experiences.model_dump()["experiences"]

        add_experienve_count = 0
        for exp_entry in experiences_list:
            # persist as Experience dataclass via append_experience
            exp_entry["step"] = steps
            try:
                append_experience(shared_session_id, steps, exp_entry, repo_dir=repo_dir)
                add_experienve_count += 1
            except Exception:
                pass
        self.logger.info(f"[Code Judge Agent] Generated {len(experiences_list)} experiences. Added {add_experienve_count} experiences for step {steps}.")
        
        return
    
    def save_best_generated_code_to_jsonl(self, repo_dir: str, full_code: list) -> None:
        code_jsonl_dir = f"{repo_dir}{self.code_json_dir_suffix}"
        os.makedirs(code_jsonl_dir, exist_ok=True)
        code_jsonl_path = f"{code_jsonl_dir}/best_generated_code.jsonl"

        with open(code_jsonl_path, "w", encoding="utf-8") as f:
            for item in full_code:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.logger.info(f"[Code Agent] Best generated code saved to {code_jsonl_path}")

    def load_current_step_code(self, repo_name: str, steps: int) -> tuple[list, str, str]:
        # load previous step data from shared memory
        shared_session_id = f"code_shared_{repo_name}"
        load = None
        generated_code = []
        try:
            load = load_code_step(shared_session_id, step=steps)
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
        steps = state["code_steps"]

        self.logger.info(f"==========CODE CHECK IN STEP {steps}===========")

        latest_code = self.load_current_step_code(repo_name, steps)

        suggested_changes = [] 
        written_files, files_fail_to_write = self.write_code_to_files(latest_code, repo_dir)
        for item in files_fail_to_write:
            suggested_changes.append({
                "summary": f"Failed to write {item}.",
                "likely_cause": "File permissions or path validity.",
                "suggested_fix": "Please check file permissions or path validity.",
                })

        feedback_text = ""
        if files_fail_to_write:
            feedback_text = f"Code JSON parsing failed in the following files: {' '.join(files_fail_to_write)}."

        test_output, error, passed, total = self.run_pytest_and_collect(dataset, repo_name, repo_dir)
        if error:
            test_status = "test cases fail to run as expected because of errors"
        else:
            test_status = f"passed {passed} out of {total}"

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
            update_code_step(shared_session_id, steps, {"test_result": test_result}, repo_dir=repo_dir)
        except Exception:
            pass

        code_decision = self.make_judge_decision(passed, total, steps, written_files)
        if code_decision['decision'] == "approve":
            feedback_text += self.generate_test_feedback(error, passed, total)
            result = None
        elif code_decision['decision'] == "reject":
            result = self.run_code_judge_agent(test_output)
            suggested_changes.extend(result)
            feedback_text = self.generate_test_feedback(error, passed, total, suggested_changes)

        # Persist structured feedback (including raw `result`) into shared memory
        try:
            shared_session_id = f"code_shared_{repo_name}"
            feedbacks = {
                "result": suggested_changes if suggested_changes is not None else [],
                "text": feedback_text
            }
            update_code_step(shared_session_id, steps, {"feedbacks": feedbacks}, repo_dir=repo_dir)
        except Exception:
            self.logger.error(f"[Code Judge Agent] Error in updating shared step record at step {steps}: {e}")
            pass

        # Experience
        if code_decision['decision'] == "reject" and steps > 1:
            try:
                self.logger.info(f"[Code Judge Agent] Summarizing experience for step {steps}...")
                self.update_experience(repo_name, steps, passed, result, repo_dir)
            except Exception as e:
                self.logger.error(f"[Code Judge Agent] Error in updating shared experiences at step {steps}: {e}")
                pass

        self.logger.info(f"[decision]: {code_decision}")
        self.logger.info(f"[feedback]: {feedback_text}")

        if code_decision['decision'] == 'approve':
            best_generated_code = load_best_generated_code(f"code_shared_{repo_name}")
            self.save_best_generated_code_to_jsonl(repo_dir, best_generated_code)
            self.write_code_to_files(best_generated_code, repo_dir)
            self.logger.info(f"[Code Judge Agent]: write best generated code to {repo_dir}")


        return {
            **state,
            "code_decision": code_decision["decision"],
            "code_feedback": feedback_text,
            "test_status": test_status,
            "code_steps": steps,
        }