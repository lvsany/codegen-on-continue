from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from utils.logger import get_logger
import os
import json
from typing import List, Dict, Union, Tuple, Literal
import re
import ast
from utils.general_utils import *
from json_repair import repair_json
from utils.extract_api import extract_api
from utils.global_state import update_global_state, get_global_state, get_state_value
import difflib
from utils.build_dependency_graph import reorder_skeleton_by_topo
from callbacks.agent_metrics_handler import AgentMetricsHandler
from langchain.tools import tool
from functools import partial
from prompt_templates.code_prompts import CodePrompts, GetFilesToUpdatePrompts
from utils.generation_schema import CODE_FILE_UPDATE_SCHEMA, CODE_JSON_SCHEMA
from memory_manager.code_shared_memory import SharedStepCodeRecord, save_code_step, update_code_step, load_code_step
from memory_manager.code_shared_memory import load_repo_experiences
from memory_manager.arch_shared_memory import SharedStepArchRecord, load_arch_step, save_arch_step
from memory_manager.skeleton_shared_memory import load_skeleton_step
from rank_bm25 import BM25Okapi
from pydantic import BaseModel, Field
from utils.construct_soft_relation import build_context_for_init_code_generation, flatten_ssat_symbols, build_soft_relation_index
from utils.construct_realized_relation import realize_ssat_relations, build_file_relation_graph, collect_related_file_codes, update_realized_relations_from_code, update_ssat_realized_from_code, remove_file_from_ssat
from utils.general_utils import invoke_with_retry

class CodeSchema(BaseModel):
    path: str = Field(description="The file path of the code file")
    code: str = Field(description="The complete code for the file")
    description: str | None = Field(default=None,  description="The description of the code file")

class CodeFileUpdateItem(BaseModel):
    path: str = Field(description="The file path of the code file to be updated")
    action: Literal["modify", "create", "remove"] = Field(description="Action to perform on the file")
    rationale: str = Field(description="The rationale for updating the file")
    suggestion: str = Field(description="Suggested modification for the file")

class CodeFileUpdateSchema(BaseModel):
    files_to_update: List[CodeFileUpdateItem] = Field(description="List of code files to be updated")

@tool(description="Search for the corresponding 'file' node in SSAT based on the file path, and return all content of that node.")
def find_ssat_of_file_by_path(path: str) -> dict:
    """Search for the corresponding "file" node in SSAT based on the file path, and return all content of that node."""
    ssat = get_state_value("ssat")
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            if file.get("path") == path:
                return file
    return None

@tool(description="Search for the current code of the file path, and return all content of that item.")
def find_code_of_file_by_path(path: str) -> dict:
    """Search for the current code of the file path, and return all content of that item."""
    code_index = get_state_value("code_by_path")
    if code_index and path in code_index.keys():
        return code_index[path]["code"]
    else:
        return None

class CodeAgent:
    CONTEXT_MAX_LENGTH = 5  
    MAX_RETRIES_PER_FILE = 3  

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.code_json_dir_suffix = "/tmp_files"

        self.tools = [find_ssat_of_file_by_path, find_code_of_file_by_path]

        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=CodePrompts.get_system_prompt(),
            response_format=ProviderStrategy(CodeSchema)
        ).with_config(callbacks=[self.metrics_handler])

        self.agent_chain_with_tools_for_get_files_to_update = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=GetFilesToUpdatePrompts.get_system_prompt(),
            response_format=ProviderStrategy(CodeFileUpdateSchema)
        ).with_config(callbacks=[self.metrics_handler])

    def reorder_skeleton(self, latest_skeleton: list) -> list:
        try:
            reordered_skeleton = reorder_skeleton_by_topo(latest_skeleton)
            self.logger.info(f"[Code Agent] Successfully reordered skeleton based on topological sort.")
            return reordered_skeleton
        except Exception as e:
            self.logger.warning(f"[Code Agent] Error in reordering skeleton by topo: {e}")
            return latest_skeleton

    def find_unimplemented_functions(self, code: str) -> List[str]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        unimplemented = []

        class PlaceholderFunctionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.class_stack = []

            def visit_ClassDef(self, node: ast.ClassDef):
                self.class_stack.append(node.name)
                self.generic_visit(node)
                self.class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef):
                if self._is_placeholder_body(node):
                    unimplemented.append(self._qualified_name(node.name))
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                if self._is_placeholder_body(node):
                    unimplemented.append(self._qualified_name(node.name))
                self.generic_visit(node)

            def _qualified_name(self, func_name: str) -> str:
                if self.class_stack:
                    return f"{self.class_stack[-1]}.{func_name}"
                return func_name

            @staticmethod
            def _is_placeholder_body(node) -> bool:
                """
                True iff function body is a known placeholder implementation.
                """
                if len(node.body) != 1:
                    return False

                stmt = node.body[0]

                # case 1: pass
                if isinstance(stmt, ast.Pass):
                    return True

                # case 2: raise NotImplementedError / UnimplementedError
                if isinstance(stmt, ast.Raise):
                    exc = stmt.exc
                    if exc is None:
                        return False

                    if isinstance(exc, ast.Name):
                        return _is_not_implemented_name(exc.id)

                    if isinstance(exc, ast.Call):
                        if isinstance(exc.func, ast.Name):
                            return _is_not_implemented_name(exc.func.id)

                return False

        def _is_not_implemented_name(name: str) -> bool:
            """
            Match NotImplementedError / UnimplementedError and common variants.
            """
            lowered = name.lower()
            return (
                "notimplemented" in lowered
                or "unimplemented" in lowered
            )

        PlaceholderFunctionVisitor().visit(tree)
        return unimplemented

    def generate_init_code(self, repo_name: str, latest_skeleton: list, steps: int) -> list:
        ssat = load_arch_step(f"arch_shared_{repo_name}").ssat
        full_code = []
        
        # preparation for context construction
        symbol_index = flatten_ssat_symbols(ssat)
        outgoing_index, incoming_index = build_soft_relation_index(ssat, latest_skeleton)
        
        for file_item in latest_skeleton:
            if not file_item["path"].endswith(".py"):
                continue
            
            self.logger.info(f"[Code Agent] Processing file: {file_item['path']}")
            
            _, context = build_context_for_init_code_generation(file_item["path"], ssat, latest_skeleton, symbol_index, outgoing_index, incoming_index)

            result = invoke_with_retry(
                self.agent_chain_with_tools,
                {
                    "messages": CodePrompts.get_init_prompt().format_messages(
                        file_item=f"- {file_item['path']}\n\n{file_item['skeleton_code']}\n",
                        context=context
                    )
                }
            )

            code_file: CodeSchema = result["structured_response"]
            code_file_dict = code_file.model_dump()

            # if unimplemented
            retries = 0
            
            while retries < self.MAX_RETRIES_PER_FILE:
                # find if there exist any fucntions unimplemented (with pass)
                unimplemented = self.find_unimplemented_functions(code_file_dict["code"])
                    
                if not unimplemented:
                    file_item["code"] = code_file_dict["code"]
                    full_code.append({
                        "path": code_file_dict["path"],
                        "code": code_file_dict["code"],
                        "diff": ""
                    })
                    ssat = update_ssat_realized_from_code(ssat=ssat, file_result=code_file_dict)
                    break

                # fix the code
                self.logger.warning(f"[Code Agent] Unimplemented functions in {file_item['path']}: {unimplemented}")
                
                messages = list(result["messages"])
                messages.extend(
                    CodePrompts.get_fix_prompt().format_messages(
                        funcs="\n".join(f"- {f}" for f in unimplemented)
                    )
                )
                result = invoke_with_retry(
                    self.agent_chain_with_tools,
                    {
                        "messages": messages
                    }
                )

                code_file: CodeSchema = result["structured_response"]
                code_file_dict = code_file.model_dump()
                
                retries += 1
                
            else:
                self.logger.error(f"[Code Agent] Error in step {steps} when generating code for file {file_item.get('path', '')} after {self.MAX_RETRIES_PER_FILE} retries")
                file_item["code"] = code_file_dict["code"]
                full_code.append({"path": code_file_dict["path"], "code": code_file_dict["code"], "diff": ""})
                
                ssat = update_ssat_realized_from_code(ssat=ssat, file_result=code_file_dict)

        ssat = self._update_ssat_with_realized_relation(full_code)
        code_by_path = {
            item["path"]: item
            for item in full_code
        }
        update_global_state({"ssat": ssat, "code_by_path": code_by_path})

        return full_code
    
    def _update_ssat_with_realized_relation(self, full_code: List[dict]):
        ssat = get_state_value("ssat")

        # generate realized relations and update ssat (update file / func nodes with realized relations)
        ssat = realize_ssat_relations(ssat, full_code)
        
        # construct outgoing / incoming index for each file
        outgoing_index, incoming_index = build_file_relation_graph(ssat)
        
        ssat["realized_relations"] = {
            "outgoing_index": outgoing_index,
            "incoming_index": incoming_index
        }
        
        update_global_state({"ssat": ssat})
        
        return ssat


    def get_files_to_update(self, feedback_text: str) -> set:
        
        context = self.collect_files_from_ssat()

        result = invoke_with_retry(
            self.agent_chain_with_tools_for_get_files_to_update,
            {
                "messages": GetFilesToUpdatePrompts.get_human_prompt().format_messages(
                    feedback=feedback_text,
                    context=context
                )
            }
        )

        structured_response : CodeFileUpdateSchema = result["structured_response"]
        files_to_update = structured_response.model_dump()["files_to_update"]

        return files_to_update
        
    def generate_iter_code(self, feedback_text: str) -> tuple[list, list]:
        repo_name = get_state_value("repo_name")

        def retrieve_relevant_experiences(query: str, repo: str, k: int = 5):
            exps = load_repo_experiences(repo)
            if not exps:
                return []
            corpus = []
            for e in exps:
                scenario = e.get("scenario", "") if isinstance(e, dict) else str(e)
                experience = e.get("experience", "") if isinstance(e, dict) else str(e)
                corpus.append((f"{scenario} {experience}").strip())
            tokenized = [doc.split() for doc in corpus]
            try:
                bm25 = BM25Okapi(tokenized)
                q_tokens = query.split()
                scores = bm25.get_scores(q_tokens)
                ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
                top = [exps[i] for i in ranked[:k]]
                return top
            except Exception as e:
                self.logger.warning(f"[Code Agent] Error in retrieving relevant experiences: {e}")
                return exps[:k]

        top_exps = retrieve_relevant_experiences(feedback_text or "", repo_name, k=3)
        self.logger.info(f"[Code Agent] Retrieved {len(top_exps)} relevant experiences for code update.")
        if top_exps:
            feedback_text += "\n\nHere are some relevant experiences:\n"
            for e in top_exps:
                for k, v in e.items():
                    feedback_text += f"{k}: {v}\n"
                    if k == 'experience':
                        feedback_text += '\n' 

        files_to_update_list = self.get_files_to_update(feedback_text)
        
        full_code, diff_code = self.update_files_iteratively(files_to_update_list)

        
        return full_code, diff_code

    def compute_code_diff(self, old_file_item: dict, new_file_item: dict) -> str:
        diff = difflib.unified_diff(
            old_file_item["code"].splitlines(),
            new_file_item["code"].splitlines(),
            fromfile=old_file_item["path"],
            tofile=new_file_item["path"],
        )
        return "\n".join(diff)
    
    def get_related_files_content(self, code_index: dict, related_files: list):
        context = ""
        for path in related_files:
            if path in code_index:
                file_item = code_index[path]
                context += f"- {path}\n\n{file_item.get('code')}\n"
        return context

    def update_files_iteratively(self, files_to_update_list: list[dict]) -> tuple[list, list]:
        
        code_index = get_state_value("code_by_path")
        ssat = get_state_value("ssat")
        realized_relations = ssat.get("realized_relations", [])
        outgoing_index = realized_relations.get("outgoing_index", {})
        incoming_index = realized_relations.get("incoming_index", {})
        
        diff_code = []
        
        for item in files_to_update_list:
            target_path = item["path"]
            action = item["action"]
            rationale = item["rationale"]
            suggestion = item["suggestion"]
            
            self.logger.info(f"[Code Agent] {action.upper()} file: {target_path}")
            
            if action == "remove":
                if target_path in code_index:
                    del code_index[target_path]
        
                ssat = remove_file_from_ssat(ssat, target_path)
                    
                for dep in outgoing_index.get(target_path, set()):
                    incoming_index.get(dep, set()).discard(target_path)
                for dep in incoming_index.get(target_path, set()):
                    outgoing_index.get(dep, set()).discard(target_path)
                outgoing_index.pop(target_path, None)
                incoming_index.pop(target_path, None)
                
                diff_code.append({"path": target_path, "diff": "File removed"})
                continue
            
            if action in ("modify", "create"):
                if action == "modify" and target_path in code_index:
                    file_item = code_index[target_path]
                else:
                    file_item = {"path": target_path, "code": ""}
        
                related_files = (outgoing_index.get(target_path, set()) | incoming_index.get(target_path, set()))
                context = self.get_related_files_content(code_index, related_files)

                result = invoke_with_retry(
                    self.agent_chain_with_tools,
                    {
                        "messages": CodePrompts.get_iter_prompt().format_messages(
                            path=target_path,
                            code=file_item["code"],
                            suggestion=suggestion,
                            rationale=rationale,
                            context=context
                        )
                    }
                )

                code_file: CodeSchema = result["structured_response"]
                code_file_dict = code_file.model_dump()

                diff_str = self.compute_code_diff(file_item, code_file_dict)
                code_file_dict["diff"] = diff_str
                diff_code.append({"path": target_path, "diff": diff_str})

                code_index[target_path] = code_file_dict
                
                ssat = update_ssat_realized_from_code(ssat=ssat, file_result=code_file_dict)
                update_global_state({"ssat": ssat})
                
                ssat = self._update_ssat_with_realized_relation(list(code_index.values()))

            else:
                self.logger.warning(f"[Code Agent] Unknown action '{action}' for file {target_path}")
        
        diff_index = {item["path"]: item.get("diff", "") for item in diff_code}
        full_code = list(code_index.values())

        update_global_state({"ssat": ssat, "code_by_path": code_index})
        

        return full_code, diff_code

    def collect_files_from_ssat(self) -> Tuple[List[Dict[str, str]], str]:
        """
        Traverse SSAT and collect all file paths and descriptions.

        Returns:
            files_text:
                path/to/file.py: description
                path/to/other.py: description
        """
        ssat = get_state_value("ssat")
        lines: List[str] = []

        for module in ssat.get("modules", []):
            for file in (module.get("files") or []):
                path = file.get("path")
                description = file.get("description", "")
                if not path:
                    continue
                lines.append(f"{path}: {description}")
        files_text = "\n".join(lines)
        return files_text

    def save_code_to_jsonl(self, repo_dir: str, steps: int, full_code: list) -> None:
        code_jsonl_dir = f"{repo_dir}{self.code_json_dir_suffix}"
        os.makedirs(code_jsonl_dir, exist_ok=True)
        code_jsonl_path = f"{code_jsonl_dir}/generated_code_{steps}.jsonl"

        with open(code_jsonl_path, "w", encoding="utf-8") as f:
            for item in full_code:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.logger.info(f"[Code Agent] Generated code saved to {code_jsonl_path}")

    def load_previous_step_data(self, repo_name: str, steps: int) -> tuple[list, str, str]:
        # load previous step data from shared memory
        shared_session_id = f"code_shared_{repo_name}"
        load = None
        if steps > 1:
            try:
                load = load_code_step(shared_session_id, step=steps - 1)
            except Exception as e:
                self.logger.error(f"[Code Agent] Error in loading previous step (step {steps - 1}) data: {e}")
                load = None

        generated_code = []
        test_status, feedback = "", ""
        # derive test_status and feedback from shared memory if available
        if load is not None:
            if getattr(load, "generated_code", []):
                generated_code = load.generated_code

            if getattr(load, "test_result", None):
                tr = load.test_result
                if isinstance(tr, dict):
                    test_status = tr.get("test_status")

            if getattr(load, "feedbacks", None):
                fb = load.feedbacks
                if isinstance(tr, dict):
                    feedback = fb.get("text")

        return generated_code, test_status, feedback

    def __call__(self, state: dict) -> dict:
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        steps = state.get("code_steps", 0) + 1

        self.logger.info(f"==========CODE GENERATION IN STEP {steps}===========")

        latest_code, test_status, feedback = self.load_previous_step_data(repo_name, steps)
        latest_skeleton = load_skeleton_step(f"skeleton_shared_{repo_name}").generated_skeleton

        if steps == 1:
            latest_skeleton = self.reorder_skeleton(latest_skeleton)
            full_code = self.generate_init_code(repo_name, latest_skeleton, steps)
            diff_code = []
        else:
            full_code, diff_code = self.generate_iter_code(feedback)

        # persist shared step record (shared session id between CodeAgent and CodeJudgeAgent)
        shared_session_id = f"code_shared_{repo_name}"
        record = SharedStepCodeRecord(
            step=steps,
            generated_code=full_code,
            diff_code=diff_code,
            test_result=None,
            feedbacks=None,
            ssat=get_state_value("ssat"),
            experiences=[],
        )
        try:
            save_code_step(shared_session_id, repo_dir, record)
        except Exception as e:
            self.logger.error(f"[Code Agent] Error in saving shared step record at step {steps}: {e}")
            pass

        self.save_code_to_jsonl(repo_dir, steps, full_code)

        update_global_state({"code_steps": steps})
        updated_state = {
            **state,
            "code_steps": steps
        }
        return updated_state
