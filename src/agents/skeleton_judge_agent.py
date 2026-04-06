from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain.tools import tool
from functools import partial
from typing import Tuple, Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
import os
from utils.logger import get_logger
from utils.general_utils import *
import logging
import re
import ast
import py_compile
import json
from utils.generation_schema import SKELETON_JUDGE_SCHEMA
from utils.global_state import update_global_state, get_global_state, get_state_value
from prompt_templates.skeleton_judge_prompt import SkeletonJudgePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from memory_manager.arch_shared_memory import load_arch_step, update_arch_step, save_arch_step, SharedStepArchRecord
from memory_manager.skeleton_shared_memory import load_skeleton_step, save_skeleton_step, update_skeleton_step
from utils.construct_soft_relation import build_soft_relations


class ScoreWithComments(BaseModel):
    score: float = Field(ge=1, le=10, description="Score from 1 (poor) to 10 (excellent)")
    comments: str = Field(description="Concise justification for the score")

class SkeletonFeedback(BaseModel):
    directory_structure_matching: ScoreWithComments = Field(description="Whether directory structure matches the expected design")
    interface_and_call_relationship_matching: ScoreWithComments = Field(description="Whether interfaces and call relationships match SSAT/UML")

class SkeletonSuggestedChange(BaseModel):
    path: str = Field(description="The file path to be changed")
    suggestion: str = Field(description="Suggested modification for this file")

class SkeletonJudgeSchema(BaseModel):
    feedback: SkeletonFeedback
    suggested_changes: List[SkeletonSuggestedChange] = Field(default_factory=list, description="List of suggested changes for specific files")
    final_score: float = Field(ge=1, le=10, description="Overall score for the skeleton evaluation")
    decision: Literal["approve", "reject"]

@tool(description="Check if the skeleton code covers all files and functions specified in the SSAT.")
def check_ssat_skeleton_coverage() -> Dict[str, Any]:
    """Check if the skeleton code covers all files and functions specified in the SSAT."""
    
    repo_name = get_state_value("repo_name")
    ssat = get_state_value("ssat")
    skeleton = load_skeleton_step(session_id=f"skeleton_shared_{repo_name}").generated_skeleton

    skeleton_by_path = {
        item["path"]: item["skeleton_code"]
        for item in skeleton
    }

    missing_files = []
    missing_functions = []
    missing_classes = []

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            path = file.get("path")
            if path not in skeleton_by_path:
                missing_files.append(path)
                continue

            code = skeleton_by_path[path]
            defined_functions, defined_classes = extract_symbols_from_code(code)

            # check functions
            for func in (file.get("functions") or []):
                if func["name"] not in defined_functions:
                    missing_functions.append(f"{path}:{func['name']}")

            # check class & class methods
            for cls in (file.get("classes") or []):
                cls_name = cls["name"]
                if cls_name not in defined_classes:
                    missing_classes.append(f"{path}:{cls_name}")
                    continue
                for method in (cls.get("methods") or []):
                    full_name = f"{cls_name}.{method['name']}"
                    if full_name not in defined_functions:
                        missing_functions.append(f"{path}:{full_name}")

    return {
        "pass": not missing_files and not missing_functions,
        "missing_files": missing_files,
        "missing_functions": missing_functions
    }

def extract_symbols_from_code(code: str) -> tuple[set[str], set[str]]:
    """Extract top-level function / classes and class.method names from skeleton code."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set(), set()
    funcs = set()
    classes = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    funcs.add(f"{node.name}.{item.name}")
    return funcs, classes

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


class SkeletonJudgeAgent:
    MAX_SKELETON_ITER = 3

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.tools = [check_ssat_skeleton_coverage, search_docs_by_keyword]

        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=SkeletonJudgePrompts.get_system_prompt(),
            response_format=ProviderStrategy(SkeletonJudgeSchema)
        ).with_config(callbacks=[self.metrics_handler])


    def write_skeleton_to_files(self, skeleton_data: any, repo_dir: str) -> tuple[bool, list]:
        written_files, error_files = [], []

        for item in skeleton_data:
            file_path = os.path.join(repo_dir, item["path"])
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(item["skeleton_code"])
                written_files.append(file_path)
            except Exception as e:
                self.logger.error(f"[Skeleton Judge Agent] Error writing file {file_path}: {e}")
                error_files.append(file_path)

        return written_files, error_files

    def remove_written_files(self, written_files: list) -> None:
        for f in written_files:
            try:
                os.remove(f)
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
    
    def serialize_skeleton_for_llm(self, latest_skeleton: list[dict]) -> str:
        parts = []

        for item in latest_skeleton:
            path = item.get("path", "<unknown>")
            code = item.get("skeleton_code", "")

            parts.append(f"\n[FILE] {path}")
            parts.append("```python")
            parts.append(code.rstrip())
            parts.append("```")

        return "\n".join(parts)

    def generate_judge_feedback(self, result: dict) -> str:
        suggestion_text = ''
        for item in result["suggested_changes"]:
            for k, v in item.items():
                suggestion_text += f"{k}: {v}\n"
                if k == 'suggestion':
                    suggestion_text += '\n'
        return suggestion_text

    def make_judge_decision(self, result: dict, steps: int) -> Dict:
        llm_decision = result["decision"]

        if steps >= self.MAX_SKELETON_ITER:
            return {
                "decision": "approve",
                "forced": True
            }

        return {
            "decision": llm_decision,
            "forced": False,
        }

    def __call__(self, state: dict) -> dict:
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        steps = state.get("skeleton_steps", 0)
        
        self.logger.info(f"==========SKELETON CHECK IN STEP {steps}===========")

        latest_arch = get_state_value("ssat")
        latest_skeleton = load_skeleton_step(session_id=f"skeleton_shared_{repo_name}", step=steps).generated_skeleton

        suggested_changes = []  
        use_llm_judge = False
        written_files, files_fail_to_write = self.write_skeleton_to_files(latest_skeleton, repo_dir)
        for item in files_fail_to_write:
            suggested_changes.append({
                "path": item,
                "suggestion": "Failed to write this file. Please check file permissions or path validity."
            })
        
        if files_fail_to_write:
            feedback_text = f"Skeleton JSON parsing failed in the following files: {' '.join(files_fail_to_write)}."

        compile_ok, compile_errors = self.check_python_compile(repo_dir)
        self.remove_written_files(written_files)
        
        if not compile_ok:
            feedback_text = f"Failed to write files: {files_fail_to_write}\n"
            feedback_text += "Additionally, skeleton failed the Python compilation check. Please correct the syntax error.\n"
            feedback_text += "\n".join(compile_errors)
            skeleton_decision = {"decision": "reject", "forced": False}
            self.logger.info(f"[decision]: {skeleton_decision}")
            self.logger.info(f"[feedback]: {feedback_text}")
            judge_result_dict = None

        else:
            use_llm_judge = True

            result = invoke_with_retry(
                self.agent_chain_with_tools,
                {
                    "messages": SkeletonJudgePrompts.get_human_prompt().format_messages(
                        architecture=json.dumps(latest_arch, ensure_ascii=False, indent=2),
                        skeleton=self.serialize_skeleton_for_llm(latest_skeleton)
                    )
                }
            )

            judge_result : SkeletonJudgeSchema = result["structured_response"]
            judge_result_dict = judge_result.model_dump()
            
            suggested_changes.extend(judge_result_dict["suggested_changes"])
            feedback_text = self.generate_judge_feedback(judge_result_dict)
            skeleton_decision = self.make_judge_decision(judge_result_dict, steps)

            self.logger.info(f"[decision]: {skeleton_decision}")
            self.logger.info(f"[feedback]: {feedback_text}")
        
        try:
            shared_session_id = f"skeleton_shared_{repo_name}"
            update_skeleton_step(
                shared_session_id,
                steps,
                {"feedbacks": {"result": result if judge_result_dict else None, "text": feedback_text}},
                repo_dir=repo_dir
            )
        except Exception as e:
            self.logger.error(f"[Skeleton Judge Agent] Error in updating shared step record at step {steps}: {e}")
            pass

        # construct soft relation, and save in arch_shared_memory & update global state
        if skeleton_decision["decision"] == "approve":
            ssat_with_soft_relation = build_soft_relations(latest_arch, latest_skeleton)
            update_global_state({"ssat": ssat_with_soft_relation})
        return {
            **state,
            "skeleton_decision": skeleton_decision["decision"],  
        }