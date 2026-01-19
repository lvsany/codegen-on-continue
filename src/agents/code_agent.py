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
import os
import json
from typing import List, Dict, Union
import re
from utils import *
from json_repair import repair_json
from memory_manager.code_memory import get_session_history
from extract_api import extract_api
import difflib
from build_dependency_graph import reorder_skeleton_by_topo
from callbacks.agent_metrics_handler import AgentMetricsHandler
from prompt_templates.code_prompts import CodePrompts, GetFilesToUpdatePrompts
from generation_schema import CODE_FILE_UPDATE_SCHEMA, CODE_JSON_SCHEMA
from memory_manager.code_shared_memory import SharedStepRecord, save_step, update_step, load_step
from memory_manager.code_shared_memory import load_repo_experiences
from rank_bm25 import BM25Okapi


class CodeAgent:
    CONTEXT_MAX_LENGTH = 5  

    def __init__(self, llm):
        self.base_llm = llm
        self.model = self.base_llm.with_structured_output(CODE_JSON_SCHEMA, method="json_schema")
        self.clean_history_runnable = RunnableLambda(clean_history)
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.code_json_dir_suffix = "/tmp_files"

    def get_session_id(self, repo_name: str) -> str:
        return f"code_agent_{repo_name}"

    def save_file_output_to_jsonl(self, path: str, file_content: str, jsonl_path: str = "generated_files.jsonl") -> None:
        if hasattr(file_content, "to_string"):
            content = file_content.to_string()
        elif hasattr(file_content, "content"):
            content = file_content.content
        else:
            content = str(file_content)
        
        if "```" in content:
            match = re.search(r"```(?:python)?\s*([\s\S]+?)\s*```", content)
            if match:
                content = match.group(1)
        
        record = {
            "path": path,
            "content": content.strip()
        }
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def reorder_skeleton_by_topo(self, latest_skeleton: list) -> list:
        try:
            reordered_skeleton = reorder_skeleton_by_topo(latest_skeleton)
            self.logger.info(f"[Code Agent] Successfully reordered skeleton based on topological sort.")
            return reordered_skeleton
        except Exception as e:
            self.logger.error(f"[Code Agent] Error in reordering skeleton by topo: {e}")
            return latest_skeleton

    def build_code_context(self, full_code: list) -> list:
        # TODO: 重新考虑上下文的获取方式
        context = []
        if len(full_code) > self.CONTEXT_MAX_LENGTH:
            # 超过最大长度：早期文件提取API，最近5个保留完整代码
            for item in full_code[:-self.CONTEXT_MAX_LENGTH]:
                api_info = extract_api(item["code"], item["path"])
                context.append({"path": item["path"], "code": api_info})
            context.extend(full_code[-self.CONTEXT_MAX_LENGTH:])
        else:
            # 未超过最大长度：保留完整代码
            context = full_code
        return context

    def generate_init_code(self, latest_skeleton: list, test_status: Dict, session_id: str, steps: int) -> list:
        full_code = []
        # 按拓扑顺序遍历文件生成代码
        for file_item in latest_skeleton:
            if file_item["path"].endswith(".py"):
                self.logger.info(f"[Code Agent] Processing file: {file_item['path']}")
                context = self.build_code_context(full_code)

                prompt = CodePrompts.init_prompt()
                input_key = "file_item"
                input_data = {
                    "file_item": file_item,
                    "context": context
                }
                code_chain = RunnableWithMessageHistory(
                    prompt | self.model,
                    get_session_history=get_session_history,
                    input_messages_key=input_key,
                    history_messages_key="history"
                )

                try:
                    result = code_chain.invoke(
                        input_data,
                        config={
                            "configurable": {"session_id": session_id, "agent": "code_agent", "step": steps},
                            "callbacks": [self.metrics_handler]
                        }
                    )
                    file_item["code"] = result["code"]
                    full_code.append({
                        "path": result.get("path", file_item["path"]),
                        "code": result["code"],
                        "diff": ""
                    })
                except Exception as e:
                    # TODO: 增加错误处理，无法正常生成时重新生成或者记录在一个list中，最后统一处理
                    self.logger.error(f"[Code Agent] Error in step {steps} when generating code for file {file_item.get('path', '')}: {e}")
                    file_item["code"] = ""
                    full_code.append({"path": file_item["path"], "code": "", "diff": ""})

        self.update_memory(session_id, latest_skeleton, None, None, test_status, steps, full_code, None)

        return full_code

    def get_files_to_update(self, feedback: str, latest_code: list, steps: int) -> set:
        get_file_update_llm = self.base_llm.with_structured_output(CODE_FILE_UPDATE_SCHEMA, method="json_schema")
        prompt = GetFilesToUpdatePrompts.get_prompt()
        input_key = "feedback"
        input_data = {
            "feedback": feedback,
            "context": latest_code
        }
        get_files_to_update_chain = RunnableWithMessageHistory(
            prompt | get_file_update_llm,
            get_session_history=get_session_history,
            input_messages_key=input_key,
            history_messages_key="history"
        )

        try:
            result = get_files_to_update_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": "none", "agent": "code_agent", "step": steps},
                    "callbacks": [self.metrics_handler]
                }
            )
            return set(result["files_to_update"]) if result["files_to_update"] else set()
        except Exception as e:
            # TODO: 错误处理
            self.logger.error(f"[Code Agent] Error in getting files to update at step {steps}: {e}")
            return set()
        
    def generate_iter_code(self, latest_code: list, feedback: str, test_status: Dict, session_id: str, steps: int) -> tuple[list, list]:
        # retrieve repo name from session_id (session_id format: code_agent_{repo_name})
        repo_name = session_id[len("code_agent_"):] if session_id.startswith("code_agent_") else session_id

        # retrieve top-k relevant experiences from repo-level experience store
        def retrieve_relevant_experiences(query: str, repo: str, k: int = 5):
            exps = load_repo_experiences(repo)
            if not exps:
                return []
            corpus = []
            for e in exps:
                scenario = e.get("scenario", "") if isinstance(e, dict) else str(e)
                experience = json.dumps(e.get("experience", {}), ensure_ascii=False) if isinstance(e, dict) else ""
                corpus.append((scenario + " " + experience).strip())
            tokenized = [doc.split() for doc in corpus]
            try:
                # TODO: 增加个阈值吧，低于阈值的也不要
                bm25 = BM25Okapi(tokenized)
                q_tokens = query.split()
                scores = bm25.get_scores(q_tokens)
                ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
                top = [exps[i] for i in ranked[:k]]
                return top
            except Exception:
                return exps[:k]

        top_exps = retrieve_relevant_experiences(feedback or "", repo_name, k=3)
        self.logger.info(f"[Code Agent] Retrieved {len(top_exps)} relevant experiences for code update.")
        if top_exps:
            feedback_with_exps = feedback + "\n\nRelevant experiences:\n" + "\n".join([f"- {e.get('experience','') if isinstance(e, dict) else str(e)}" for e in top_exps])
            # self.logger.info(f"[Code Agent] Retrieved {len(top_exps)} relevant experiences for code update.")
        else:
            feedback_with_exps = feedback

        files_to_update_set = self.get_files_to_update(feedback_with_exps, latest_code, steps)
        context = self.build_iter_context(latest_code, files_to_update_set)
        full_code, diff_code = self.update_files_iteratively(latest_code, files_to_update_set, context, feedback, session_id, steps)
        self.update_iter_context(context, full_code)
        self.update_memory(session_id, None, latest_code, feedback, test_status, steps, full_code, diff_code)
        return full_code, diff_code

    def build_iter_context(self, latest_code: list, files_to_update_set: set) -> list:
        context = []
        for file_item in latest_code:
            if file_item["path"] not in files_to_update_set:
                api_info = extract_api(file_item["code"], file_item["path"])
                context.append({"path": file_item["path"], "code": api_info})
        return context

    def update_single_file(self, file_item: dict, context: list, feedback: str, history_str: str, session_id: str, steps: int) -> tuple[dict, str]:
        prompt = CodePrompts.iter_prompt()
        input_key = "step"
        input_data = {
            "file_item": file_item,
            "feedback": feedback,
            "context": context,
            "history_str": history_str
        }
        iter_code_chain = RunnableWithMessageHistory(
            self.clean_history_runnable | prompt | self.model,
            get_session_history=get_session_history,
            input_messages_key=input_key,
            history_messages_key="history"
        )

        try:
            result = iter_code_chain.invoke(
                input_data,
                config={
                    "configurable": {"session_id": session_id, "step": steps, "feedback": feedback},
                    "callbacks": [self.metrics_handler]
                }
            )
            diff_str = self.compute_code_diff(file_item, result)
            return result, diff_str
        except Exception as e:
            # TODO: 增加错误处理，无法正常生成时重新生成或者记录在一个list中，最后统一处理
            self.logger.error(f"[Code Agent] Error in step {steps} when updating code for file {file_item.get('path', '')}: {e}")
            return file_item, "No valid diff"

    def compute_code_diff(self, old_file_item: dict, new_file_item: dict) -> str:
        diff = difflib.unified_diff(
            old_file_item["code"].splitlines(),
            new_file_item["code"].splitlines(),
            fromfile=old_file_item["path"],
            tofile=new_file_item["path"],
        )
        return "\n".join(diff)

    def update_files_iteratively(self, latest_code: list, files_to_update_set: set, context: list, feedback: str, session_id: str, steps: int) -> tuple[list, list]:
        full_code = []
        diff_code = []
        
        for file_item in latest_code:
            diff_str = ""
            if file_item["path"] in files_to_update_set:
                self.logger.info(f"[Code Agent] Updating file: {file_item['path']}")
                memory = get_session_history(session_id)
                history_str = memory.load_memory_variables({"feedback": feedback})["history"]
                file_item, diff_str = self.update_single_file(file_item, context, feedback, history_str, session_id, steps)
                diff_code.append({"path": file_item["path"], "diff": diff_str})
            
            full_code.append({"path": file_item["path"], "code": file_item["code"], "diff": diff_str})
        
        return full_code, diff_code

    def update_iter_context(self, context: list, full_code: list) -> None:
        for file_item in full_code:
            context.append({"path": file_item["path"], "code": extract_api(file_item["code"], file_item["path"])})

    def update_memory(self, session_id: str, latest_skeleton: list, latest_code: list, feedback: str, test_status: Dict, steps: int, full_code: list, diff_code: list) -> None:
        if steps > 1:
            memory = get_session_history(session_id)
            memory.save_context(
                {"latest_code": latest_code, "feedback": feedback, "test_status": test_status, "step": steps},
                {"result": full_code, "diff_code": diff_code}
            )
        else:
            memory = get_session_history(session_id)
            memory.save_context(
                {"latest_skeleton": latest_skeleton, "test_status": test_status, "step": steps},
                {"result": full_code}
            )

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
                load = load_step(shared_session_id, step=steps - 1)
            except Exception:
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
        dataset = state["dataset"]
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        latest_skeleton = state["latest_skeleton"]
        # latest_code = state.get("latest_code", "")
        steps = state.get("code_steps", 0)
        # feedback = state.get("code_feedback", "")
        # test_status = state.get("test_status", {})
        session_id = self.get_session_id(repo_name)

        steps += 1
        self.logger.info(f"==========CODE GENERATION IN STEP {steps}===========")

        latest_code, test_status, feedback = self.load_previous_step_data(repo_name, steps)

        if steps == 1:
            latest_skeleton = self.reorder_skeleton_by_topo(latest_skeleton)
            full_code = self.generate_init_code(latest_skeleton, {}, session_id, steps)
        else:
            full_code, _ = self.generate_iter_code(latest_code, feedback, {}, session_id, steps)

        # persist shared step record (shared session id between CodeAgent and CodeJudgeAgent)
        shared_session_id = f"code_shared_{repo_name}"
        record = SharedStepRecord(
            step=steps,
            generated_code=full_code,
            test_result=None,
            feedbacks=None,
            experiences=[],
        )
        try:
            save_step(shared_session_id, repo_dir, record)
        except Exception:
            pass

        self.save_code_to_jsonl(repo_dir, steps, full_code)

        updated_state = {
            **state,
            "latest_code": full_code,
            "code_steps": steps,
            "test_status": test_status,
            "dataset": dataset,
            "repo_dir": repo_dir
        }
        return updated_state
