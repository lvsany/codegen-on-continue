from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from functools import partial
from utils.logger import get_logger
from utils.general_utils import *
import logging
import os
import re
import json
from deepdiff import DeepDiff
import difflib
from utils.generation_schema import SKELETON_JSON_SCHEMA
from utils.global_state import update_global_state, get_global_state, get_state_value
from prompt_templates.skeleton_prompts import SkeletonPrompts, GetSkeletonFilesToUpdatePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from typing import Tuple, Dict, Any, Optional, List, Literal
from memory_manager.skeleton_shared_memory import SharedStepSkeletonRecord, load_skeleton_step, save_skeleton_step, update_skeleton_step
from memory_manager.arch_shared_memory import SharedStepArchRecord, load_arch_step
from pydantic import BaseModel, Field

class SkeletonCodeSchema(BaseModel):
    path: str = Field(description="The file path of the code file.")
    skeleton_code: str = Field(description="The skeleton code for the file, with function bodies replaced with `pass`.")

class SkeletonFileUpdateItem(BaseModel):
    path: str = Field(description="The file path of the skeleton file to be updated.")
    action: Literal["modify", "create", "remove"] = Field(description="The action to perform on the skeleton file.")
    rationale: str = Field(description="The rationale for updating the file.")
    suggestion: str = Field(description="The suggestion for modifying the file.")

class SkeletonFileUpdateSchema(BaseModel):
    files_to_update: List[SkeletonFileUpdateItem] = Field(description="The skeleton files to be updated.")

@tool(description="Convert the current project ssat structure into the format {path: [symbols]} and return a dict.\nSymbols include function names, class names, class methods (in the form of class.method), and class attributes (in the form of class.attribute).")
def flatten_ssat_symbols() -> dict:
    """
    Convert the current project ssat structure into the format {path: [symbols]} and return a dict.
    Symbols include function names, class names, class methods (in the form of class.method), and class attributes (in the form of class.attribute).
    """
    ssat = get_state_value("ssat")
    flat = {}
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            path = file.get("path")
            symbols = []
            
            for func in (file.get("functions") or []):
                if "name" in func:
                    symbols.append(func["name"])
            
            for cls in (file.get("classes") or []):
                cls_name = cls.get("name")
                if cls_name:
                    symbols.append(cls_name)
                    
                    for attr in (cls.get("attributes") or []):
                        attr_name = attr.get("name")
                        if attr_name:
                            symbols.append(f"{cls_name}.{attr_name}")
                    
                    for method in (cls.get("methods") or []):
                        method_name = method.get("name")
                        if method_name:
                            symbols.append(f"{cls_name}.{method_name}")
            flat[path] = symbols
    return flat

@tool(description="Search for the corresponding 'file' node in SSAT based on the file path, and return all content of that node.")
def find_ssat_of_file_by_path(path: str) -> dict:
    """Search for the corresponding "file" node in SSAT based on the file path, and return all content of that node."""
    ssat = get_state_value("ssat")
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            if file.get("path") == path:
                return file
    return None

@tool(description="Return the skeleton code of the given path.")
def find_skeleton_of_file_by_path(path: str) -> dict:
    """Return the skeleton code of the given path."""
    skeleton = get_state_value("skeleton_by_path")
    if skeleton:
        if path in skeleton.keys():
            return skeleton[path]["skeleton_code"]
    return None


class SkeletonAgent:

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.skeleton_json_dir_suffix = "/tmp_files"
        
        self.tools = [find_ssat_of_file_by_path, find_skeleton_of_file_by_path, flatten_ssat_symbols]

        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=SkeletonPrompts.get_system_prompt(),
            response_format=ProviderStrategy(SkeletonCodeSchema)
        ).with_config(callbacks=[self.metrics_handler])

        self.agent_chain_with_tools_for_get_files_to_update = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=GetSkeletonFilesToUpdatePrompts.get_system_prompt(),
            response_format=ProviderStrategy(SkeletonFileUpdateSchema)
        ).with_config(callbacks=[self.metrics_handler])

    def generate_first_skeleton(self, ssat: Dict[str, Any]) -> List[Dict[str, Any]]:
        skeleton_by_path = {}

        for module in ssat.get("modules", []):
            files = (module.get("files") or [])
            for file_item in files:
                path = file_item['path']
                if path.endswith(".py"):

                    self.logger.info(f"[Skeleton Agent] Processing file: {path}")

                    result = invoke_with_retry(
                        self.agent_chain_with_tools,
                        {
                            "messages": SkeletonPrompts.get_init_human_prompt().format_messages(
                                path=path,
                                file_ssat=json.dumps(file_item, ensure_ascii=False, indent=2)
                            )
                        }
                    )

                    file_skeleton: SkeletonCodeSchema = result["structured_response"]
                    file_skeleton_dict = file_skeleton.model_dump()
                    skeleton_by_path[file_skeleton_dict['path']] = file_skeleton_dict
                    update_global_state({"skeleton_by_path": skeleton_by_path})
                    
        return list(skeleton_by_path.values())


    def generate_iter_skeleton(self, repo_name: str, ssat: Dict[str, Any], steps: int) -> List[Dict[str, Any]]:
        # get files to update
        prev_step = load_skeleton_step(session_id=f"skeleton_shared_{repo_name}", step=steps-1)
        latest_skeleton = prev_step.generated_skeleton
        suggested_changes = prev_step.feedbacks.get("text", "")
        result = invoke_with_retry(
            self.agent_chain_with_tools_for_get_files_to_update,
            {
                "messages": GetSkeletonFilesToUpdatePrompts.get_human_prompt().format_messages(
                    suggested_changes=suggested_changes
                )
            }
        )

        files_to_update_response: SkeletonFileUpdateSchema = result['structured_response']
        files_to_update = files_to_update_response.model_dump()['files_to_update']

        skeleton_by_path: Dict[str, Dict[str, Any]] = {
            item["path"]: dict(item)
            for item in latest_skeleton
            if "path" in item
        }
        
        for file_item in files_to_update:
            path = file_item["path"]
            self.logger.info(f"[Skeleton Agent] Processing file: {path}")
            
            if file_item['action'] == 'remove':
                if path in skeleton_by_path:
                    skeleton_by_path.pop(path)
                continue

            prev_item = skeleton_by_path.get(path)
            if prev_item:
                previous_file_skeleton = f'File: {path}\n```python\n{prev_item["skeleton_code"]}\n```\n'
            else:
                previous_file_skeleton = f"No previous skeleton for {path} available."
                
            file_ssat = ''
            for module in ssat.get("modules", []):
                for file in (module.get("files") or []):
                    if file.get("path") == path:
                        file_ssat = json.dumps(file, ensure_ascii=False, indent=2)

            result = invoke_with_retry(
                self.agent_chain_with_tools,
                {
                    "messages": SkeletonPrompts.get_iter_human_prompt().format_messages(
                        path=path,
                        previous_file_skeleton=previous_file_skeleton,
                        file_ssat=file_ssat,
                        action=file_item['action'],
                        rationale=file_item['rationale'],
                        suggestion=file_item['suggestion']
                    )
                }
            )

            file_skeleton: SkeletonCodeSchema = result["structured_response"]
            file_skeleton_dict = file_skeleton.model_dump()
            if path in skeleton_by_path.keys():
                skeleton_by_path.pop(path)
            skeleton_by_path[file_skeleton_dict['path']] = file_skeleton_dict
            update_global_state({"skeleton_by_path": skeleton_by_path})

        return list(skeleton_by_path.values())
    
    def _update_shared_skeleton_memory(self, repo_name: str, repo_dir: str, steps: int, skeleton: List[Dict[str, Any]]) -> None:
        shared_session_id = f"skeleton_shared_{repo_name}"

        if steps == 1:
            record = SharedStepSkeletonRecord(
                step=steps,
                generated_skeleton=skeleton,
                feedbacks=None
            )
            try:
                save_skeleton_step(shared_session_id, repo_dir, record)
            except Exception as e:
                self.logger.error(f"[Skeleton Agent] Error in saving shared step record at step {steps}: {e}")

        else:
            prev_skeleton = load_skeleton_step(shared_session_id, step=steps-1).generated_skeleton
            prev_skeleton_map = {
                item["path"]: item.get("skeleton_code", "")
                for item in prev_skeleton
                if "path" in item
            }

            updated_skeleton = []
            for item in skeleton:
                path = item.get("path")
                current_skeleton = item.get("skeleton_code", "")

                new_item = dict(item)  

                if path in prev_skeleton_map:
                    prev_file_skeleton = prev_skeleton_map[path]
                else:
                    prev_file_skeleton = ""

                skeleton_diff = difflib.unified_diff(
                    prev_file_skeleton.splitlines(),
                    current_skeleton.splitlines(),
                    fromfile="previous",
                    tofile="current",
                )
                
                skeleton_diff_str = "\n".join(skeleton_diff)
                new_item["diff"] = skeleton_diff_str
                updated_skeleton.append(new_item)

            record = SharedStepSkeletonRecord(
                step=steps,
                generated_skeleton=updated_skeleton,
                feedbacks=None
            )
            try:
                save_skeleton_step(shared_session_id, repo_dir, record)
            except Exception as e:
                self.logger.error(f"[Skeleton Agent] Error in updating shared step record at step {steps}: {e}")


    def save_skeleton_json(self, repo_dir: str, steps: int, skeleton: list) -> None:
        skeleton_json_dir = f"{repo_dir}{self.skeleton_json_dir_suffix}"
        os.makedirs(skeleton_json_dir, exist_ok=True)
        skeleton_json_path = f"{skeleton_json_dir}/skeleton_{steps}.json"

        try:
            with open(skeleton_json_path, "w", encoding="utf-8") as f:
                json.dump(skeleton, f, indent=2, ensure_ascii=False)
            self.logger.info(f"[Skeleton Agent] Skeleton JSON saved to {skeleton_json_path}")
        except Exception as e:
            self.logger.warning(f"[Skeleton Agent] Could not save skeleton JSON to file: {e}")


    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        steps = state.get("skeleton_steps", 0) + 1

        self.logger.info(f"==========SKELETON GENERATION IN STEP {steps}===========")

        ssat = load_arch_step(session_id=f"arch_shared_{repo_name}").ssat

        if steps == 1:
            skeleton = self.generate_first_skeleton(ssat)
        else:
            skeleton = self.generate_iter_skeleton(repo_name, ssat, steps)

        self._update_shared_skeleton_memory(repo_name, repo_dir, steps, skeleton)
        self.save_skeleton_json(repo_dir, steps, skeleton)

        updated_state = {
            **state,
            "skeleton_steps": steps
        }
        update_global_state({"skeleton_steps": steps})
        return updated_state
