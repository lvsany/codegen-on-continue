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
from json_repair import repair_json
from deepdiff import DeepDiff
from utils.generation_schema import SSAT_JSON_SCHEMA
from utils.global_state import update_global_state, get_global_state, get_state_value
from prompt_templates.architecture_prompts import ArchitecturePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from typing import Tuple, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from memory_manager.arch_shared_memory import SharedStepArchRecord, load_arch_step, save_arch_step, update_arch_step
from utils.general_utils import invoke_with_retry


class Parameter(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class Function(BaseModel):
    name: str
    description: str
    parameters: List[Parameter]
    return_type: str

class ClassAttribute(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class Class(BaseModel):
    name: str
    description: str
    attributes: Optional[List[ClassAttribute]] = Field(default_factory=list)
    methods: Optional[List[Function]] = Field(default_factory=list)

class GlobalVariable(BaseModel):
    name: str
    type: str
    description: str

class GlobalBlock(BaseModel):
    description: str

class GlobalCode(BaseModel):
    globalVariables: Optional[List[GlobalVariable]] = Field(default_factory=list)
    globalBlocks: Optional[List[GlobalBlock]] = Field(default_factory=list)

class File(BaseModel):
    name: str
    path: str
    description: str

    global_code: Optional[GlobalCode] = None
    classes: Optional[List[Class]] = Field(default_factory=list)
    functions: Optional[List[Function]] = Field(default_factory=list)

class Module(BaseModel):
    name: str
    description: str
    files: List[File]

class SemanticSoftwareArchitectureTree(BaseModel):
    modules: List[Module]


@tool
def get_prd() -> str:
    """Return the PRD document of the repository."""
    return get_state_value("prd")

@tool
def get_uml_class() -> str:
    """Return the UML class diagram of the repository."""
    return get_state_value("uml_class")

@tool
def get_uml_sequence() -> str:
    """Return the UML sequence diagram of the repository."""
    return get_state_value("uml_sequence")

@tool
def get_arch_design() -> str:
    """Return the architecture design document of the repository."""
    return get_state_value("arch_design")

@tool(description="Retrieve the project requirement information, including the UML class diagram "
        "and the architecture design document. Use this tool when you need to understand "
        "the system structure, expected modules, or implementation requirements before "
        "generating or verifying code.")
def get_requirement() -> str:
    uml_class = get_state_value("uml_class")
    arch_design = get_state_value("arch_design")
    requirement = f"""
# UML Class Diagram
{uml_class}

# Architecture Design
{arch_design}
"""
    return requirement

class ArchitectureAgent:

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler() 
        self.arch_json_dir_suffix = "/tmp_files"
        self.tools = [get_requirement]

        self.agent_chain = create_agent(
            model=self.model,
            system_prompt=ArchitecturePrompts.get_system_prompt(),
            response_format=ProviderStrategy(SemanticSoftwareArchitectureTree)
        ).with_config(callbacks=[self.metrics_handler])

        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=ArchitecturePrompts.get_system_prompt(),
            response_format=ProviderStrategy(SemanticSoftwareArchitectureTree)
        ).with_config(callbacks=[self.metrics_handler])

    
    def get_last_step_info(self, repo_name: str, steps: int) -> tuple[int, int]:
        shared_session_id = f"arch_shared_{repo_name}"
        load = None
        if steps > 1:
            try:
                load = load_arch_step(shared_session_id, step=steps-1)
            except Exception:
                load = None

        return load.ssat if load is not None else None, load.feedbacks if load is not None else None


    def save_arch_json(self, repo_dir: str, steps: int, arch_data: dict) -> None:
        arch_json_dir = f"{repo_dir}{self.arch_json_dir_suffix}"
        
        os.makedirs(arch_json_dir, exist_ok=True)
        arch_json_path = f"{arch_json_dir}/architecture_{steps}.json"
        
        try:
            with open(arch_json_path, "w", encoding="utf-8") as f:
                json.dump(arch_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"[Architecture Agent] Architecture JSON saved to {arch_json_path}")
        except Exception as e:
            self.logger.warning(f"[Architecture Agent] Could not save architecture JSON to file: {e}")
        

    def run_architecture_agent(self, steps: int, latest_arch: Dict[str, Any], feedback: str):
        if steps <= 1:
            result = invoke_with_retry(
                self.agent_chain,
                {
                    "messages": ArchitecturePrompts.get_init_human_prompt().format_messages(
                        prd=get_state_value("prd"),
                        uml_class=get_state_value("uml_class"),
                        uml_sequence=get_state_value("uml_sequence"),
                        arch_design=get_state_value("arch_design")
                    )
                }
            )

        else:
            result = invoke_with_retry(
                self.agent_chain_with_tools,
                {
                    "messages": ArchitecturePrompts.get_iter_human_prompt().format_messages(
                        latest_arch=json.dumps(latest_arch, ensure_ascii=False, indent=2),
                        feedback=feedback
                    )
                }
            )

        ssat: SemanticSoftwareArchitectureTree = result["structured_response"]
        return ssat.model_dump()
    

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        steps = state.get("arch_steps", 0) + 1

        self.logger.info(f"==========ARCHITECTURE GENERATION IN STEP {steps}===========")

        latest_arch, feedback = self.get_last_step_info(repo_name, steps)

        result = self.run_architecture_agent(steps, latest_arch, feedback)

        shared_session_id = f"arch_shared_{repo_name}"
        record = SharedStepArchRecord(
            step=steps,
            ssat=result,
            feedbacks=None
        )
        try:
            save_arch_step(shared_session_id, repo_dir, record)
        except Exception as e:
            self.logger.error(f"[Architecture Agent] Error in saving shared step record at step {steps}: {e}")

        self.save_arch_json(repo_dir, steps, result)

        updated_state = {
            **state,
            "arch_steps": steps,
            "ssat": result
        }
        update_global_state({"arch_steps": steps, "ssat": result})
        return updated_state