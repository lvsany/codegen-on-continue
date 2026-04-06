from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain.tools import tool
from pydantic import BaseModel, Field
import os
from utils.logger import get_logger
from utils.general_utils import *
import logging
import re
from deepdiff import DeepDiff
from functools import partial
from utils.generation_schema import ARCH_JUDGE_JSON_SCHEMA
from utils.global_state import update_global_state, get_global_state, get_state_value
from typing import Tuple, Dict, Any, Optional, Literal
from prompt_templates.arch_judge_prompts import ArchJudgePrompts
from callbacks.agent_metrics_handler import AgentMetricsHandler
from memory_manager.arch_shared_memory import SharedStepArchRecord, load_arch_step, save_arch_step, update_arch_step
import time
from pydantic import ValidationError

class ScoreWithComments(BaseModel):
    score: float = Field(ge=1, le=10, description="Score from 1 to 10")
    comments: str

class ArchitectureFeedback(BaseModel):
    requirement_coverage: ScoreWithComments
    consistency_with_provided_information: ScoreWithComments
    interface_consistency: ScoreWithComments
    dependency_relations: ScoreWithComments

class ArchitectureJudgeSchema(BaseModel):
    feedback: ArchitectureFeedback
    final_score: float = Field(
        ge=1,
        le=10,
        description="Overall score for the architecture evaluation"
    )
    decision: Literal["approve", "reject"]
    suggestions: List[str]


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

    return requirement.strip()

def get_ssat_by_step(repo_name: str, steps: int) -> tuple[int, int]:
    shared_session_id = f"arch_shared_{repo_name}"
    try:
        load = load_arch_step(shared_session_id, step=steps)
    except Exception:
        load = None

    return load.ssat if load is not None else None

@tool(description="Return the diff between SSAT of the current step and the previous step.")
def get_diff_with_previous_ssat() -> str:
    """Return the diff between SSAT of the current step and the previous step."""

    repo_name = get_state_value("repo_name")
    steps = get_state_value("arch_steps")

    if steps <= 1:
        return None
    new_ssat = get_ssat_by_step(repo_name, steps)
    old_ssat = get_ssat_by_step(repo_name, steps-1)
    try:
        arch_diff = json.dumps(DeepDiff(old_ssat, new_ssat, ignore_order=True), indent=2, default=str)
        return arch_diff
    except Exception as e:
        return None

@tool(description="Check the structural integrity of the SSAT.")
def check_ssat_structure():
    """Check the structural integrity of the SSAT."""
    
    ssat = get_state_value("ssat")

    violations = []

    if not ssat.get("modules"):
        violations.append({
            "level": "error",
            "rule": "no_modules",
            "location": "SSAT",
            "message": "SSAT contains no modules."
        })
        return violations

    for module in ssat["modules"]:
        if not module.get("files"):
            violations.append({
                "level": "error",
                "rule": "module_empty",
                "location": f"Module: {module['name']}",
                "message": "Module has no files."
            })

        for file in (module.get("files") or []):
            has_content = any(
                file.get(k) for k in ["classes", "functions", "global_code"]
            )
            if not has_content:
                violations.append({
                    "level": "warning",
                    "rule": "empty_file",
                    "location": f"File: {file.get('path', file['name'])}",
                    "message": "File contains no classes, functions, or global code."
                })

    return violations
   
def extract_uml_semantics(uml_text: str) -> dict:

    semantics = {
        "classes": {},
        "global_functions": []
    }

    uml_text = extract_first_mermaid_block(uml_text)
    if not uml_text:
        return semantics
    parsed_classes = extract_classes_from_mermaid(uml_text)

    for class_name, info in parsed_classes.items():
        if class_name.lower() in {"global_functions", "globalfunctions"}:
            semantics["global_functions"].extend(info.get("methods", []))
        else:
            semantics["classes"][class_name] = info

    return semantics


def extract_classes_from_mermaid(class_diagram: str) -> dict:
    """
    Extract class semantics from a mermaid classDiagram block.

    - Supports empty classes
    - Supports attributes / methods with or without visibility modifiers
    - Ignores parameter details
    """

    def normalize_member_name(name: str) -> str:
        return name.lstrip("+-#").strip()

    classes = {}

    class_blocks = re.findall(
        r"class\s+(\w+)\s*\{([^}]*)\}",
        class_diagram,
        re.DOTALL
    )

    for class_name, body in class_blocks:
        attributes = []
        methods = []

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # method
            if "(" in line and ")" in line:
                raw_name = line.split("(", 1)[0].strip()
                method_name = normalize_member_name(raw_name)
                methods.append(method_name)
            else:
                # attribute
                raw_name = line.split(":", 1)[0].strip()
                attr_name = normalize_member_name(raw_name)
                attributes.append(attr_name)

        classes[class_name] = {
            "attributes": attributes,
            "methods": methods
        }

    return classes

def extract_first_mermaid_block(text: str) -> str:
    """
    Assumption:
    - Dataset is well-constructed
    - The FIRST mermaid block is ALWAYS the UML class diagram
    """
    matches = re.findall(r"```mermaid(.*?)```", text, re.DOTALL)
    if not matches:
        return None
    return matches[0].strip()

def extract_ssat_interfaces(ssat: dict) -> dict:
    """
    Extract class interfaces from SSAT.

    Returns:
    {
        "ClassName": {
            "methods": set([...]),
            "attributes": set([...])
        }
    }
    """
    interfaces = {}

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            for cls in (file.get("classes") or []):
                class_name = cls.get("name")
                if not class_name:
                    continue

                methods = {m.get("name") for m in (cls.get("methods") or []) if m.get("name")}
                attributes = {a.get("name") for a in (cls.get("attributes") or []) if a.get("name")}

                interfaces[class_name] = {
                    "methods": methods,
                    "attributes": attributes
                }

    return interfaces

def extract_ssat_global_functions(ssat: dict) -> set[str]:
    """
    Extract all global (file-level) function names from SSAT.

    Returns:
        set[str]
    """
    functions = set()

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            for func in (file.get("functions") or []):
                name = func.get("name")
                if name:
                    functions.add(name)

    return functions

@tool(description="Check the interface completeness of the SSAT, including classes and global functions.")
def check_interface_completeness() -> dict:
    """Check the interface completeness of the SSAT, including classes and global functions."""
    
    ssat = get_state_value("ssat")
    ssat_interfaces = extract_ssat_interfaces(ssat)
    ssat_global_functions = extract_ssat_global_functions(ssat)

    uml_text = get_state_value("uml_class")
    uml_semantics = extract_uml_semantics(uml_text)
    uml_classes = uml_semantics["classes"]
    uml_global_functions = uml_semantics["global_functions"]

    missing_items = []

    total_expected = 0
    total_missing = 0

    for class_name, uml_info in uml_classes.items():
        uml_methods = set(uml_info.get("methods", []))
        uml_attrs = set(uml_info.get("attributes", []))

        total_expected += len(uml_methods) + len(uml_attrs)

        ssat_info = ssat_interfaces.get(class_name)
        if not ssat_info:
            total_missing += len(uml_methods) + len(uml_attrs)
            missing_items.append(
                f"Class `{class_name}` is defined in UML but missing in SSAT."
            )
            continue

        missing_methods = uml_methods - ssat_info["methods"]
        for m in missing_methods:
            total_missing += 1
            missing_items.append(
                f"Method `{class_name}.{m}` declared in UML but missing in SSAT."
            )

        missing_attrs = uml_attrs - ssat_info["attributes"]
        for a in missing_attrs:
            total_missing += 1
            missing_items.append(
                f"Attribute `{class_name}.{a}` declared in UML but missing in SSAT."
            )

    for fn in uml_global_functions:
        total_expected += 1
        if fn not in ssat_global_functions:
            total_missing += 1
            missing_items.append(
                f"Global function `{fn}` declared in UML (via Global_functions) "
                "but missing in SSAT global functions."
            )

    comments = (
        "All UML-declared interfaces are reflected in SSAT."
        if total_missing == 0
        else f"{total_missing} out of {total_expected} UML-declared interfaces are missing in SSAT."
    )

    return {
        "missing": missing_items,
        "comments": comments
    }

def extract_files_from_design_tree(design_text: str):
    """
    Parse the directory tree in architecture design and return file paths.

    Returns:
        set[str]: file paths like {"trailscraper/cli.py", ...}
    """

    tree_pattern = r"```[^\n]*\n(.*?)```"
    match = re.search(tree_pattern, design_text, re.S)

    if not match:
        return set()

    tree_text = match.group(1)

    files = set()
    stack = []

    for line in tree_text.splitlines():

        if "──" not in line:
            continue

        # determine depth
        indent = line.index("├") if "├" in line else line.index("└")
        depth = indent // 4

        name = line.split("──")[-1].strip()

        # adjust stack
        stack = stack[:depth]

        if "." not in name:  # directory
            stack.append(name)
        else:
            path = "/".join(stack + [name])
            files.add(path)

    return files


def extract_files_from_ssat(ssat):
    files = set()

    for module in ssat.get("modules", []):
        for file in module.get("files", []):
            files.add(file["path"])

    return files


@tool(description="Identify Python files that are defined in the architecture design directory tree but missing from the SSAT file structure.")
def find_missing_files():
    design_text = get_state_value("arch_design")
    ssat = get_state_value("ssat")

    design_files = extract_files_from_design_tree(design_text)
    design_py_files = {f for f in design_files if f.endswith(".py")}
    ssat_files = extract_files_from_ssat(ssat)

    return design_py_files - ssat_files



def search_in_text(text: str, query: str) -> List[str]:
    """
    Return full sentences containing the query.
    """
    
    if not text or not query:
        return []

    # split by blank lines (two or more newlines)
    PARAGRAPH_SPLIT_REGEX = re.compile(r'\n\s*\n+')
    paragraphs = PARAGRAPH_SPLIT_REGEX.split(text)

    results = []

    for para in paragraphs:
        if re.search(re.escape(query), para, flags=re.IGNORECASE):
            cleaned = para.strip()
            if cleaned:
                results.append(cleaned)

    return results


@tool(description="Search relevant sections in the PRD, UML, and Architecture Design documents using "
        "specific keywords. The query should contain concrete entities such as file names, "
        "class names, function names, API names, or domain terms (e.g., 'cli.py', "
        "'generate_policy', 'CloudTrail records', 'download logs from S3'). "
        "Avoid vague or abstract queries like 'function modules', 'dependency relations', "
        "or 'system architecture', because keyword search cannot retrieve useful results "
        "with such terms.")
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

class ArchJudgeAgent:
    MAX_ARCH_ITER = 3

    def __init__(self, llm):
        self.model = llm
        self.logger = get_logger()
        self.metrics_handler = AgentMetricsHandler()
        self.tools = [
            get_requirement,
            get_diff_with_previous_ssat, check_ssat_structure,
            check_interface_completeness, search_docs_by_keyword, find_missing_files
            ]
        
        self.agent_chain_with_tools = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=ArchJudgePrompts.get_system_prompt(),
            response_format=ProviderStrategy(ArchitectureJudgeSchema)
        ).with_config(callbacks=[self.metrics_handler])

    def validate_latest_arch(self, latest_arch: any) -> tuple[bool, str]:
        if latest_arch is None or latest_arch == "":
            return False, "No valid architecture generated in the previous step. Please ensure the output is strictly valid JSON."
        return True, ""


    def run_arch_judge_agent(self, state: dict, latest_arch: dict, steps: int) -> dict:

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                result = invoke_with_retry(
                    self.agent_chain_with_tools,
                    {
                        "messages": ArchJudgePrompts.get_human_prompt().format_messages(
                            architecture=json.dumps(latest_arch, ensure_ascii=False, indent=2)
                        )
                    }
                )
                judge_result: ArchitectureJudgeSchema = result["structured_response"]
                break
            except Exception as e:
                last_error = e
                self.logger.warning(f"ArchitectureJudge schema validation failed, retry {attempt + 1}/{max_retries}")
        else:
            raise last_error

        return judge_result.model_dump()

    def generate_judge_feedback(self, result: dict) -> str:
        suggestion_text = '\n'.join(result["suggestions"])
        return suggestion_text

    def make_judge_decision(self, result: dict, steps: int) -> tuple[bool, str]:
        llm_decision = result["decision"]

        if steps >= self.MAX_ARCH_ITER:
            return {
                "decision": "approve",
                "forced": True
            }

        return {
            "decision": llm_decision,
            "forced": False
        }

    def __call__(self, state: dict) -> dict:
        repo_name = state["repo_name"]
        repo_dir = state["repo_dir"]
        steps = state["arch_steps"]


        self.logger.info(f"==========ARCHITECTURE CHECK IN STEP {steps}===========")

        latest_arch = get_ssat_by_step(repo_name, steps)
        is_arch_valid, feedback_text = self.validate_latest_arch(latest_arch)
        if not is_arch_valid:
            arch_decision = {"decision": "reject", "forced": False}
        else:
            result = self.run_arch_judge_agent(state, latest_arch, steps)
            feedback_text = self.generate_judge_feedback(result)
            arch_decision = self.make_judge_decision(result, steps)

        try:
            shared_session_id = f"arch_shared_{repo_name}"
            update_arch_step(
                shared_session_id,
                steps,
                {"feedbacks": {"result": result if is_arch_valid else None, "text": feedback_text if is_arch_valid else ''}},
                repo_dir=repo_dir
            )
        except Exception as e:
            self.logger.error(f"[Architecture Judge Agent] Error in updating shared step record at step {steps}: {e}")
            pass

        self.logger.info(f"[decision]: {arch_decision}")
        self.logger.info(f"[feedback]: {feedback_text}")
        if arch_decision["decision"] == "reject":
            self.logger.info(f"Architecture not approved, continuing to next iteration.")
        else:
            self.logger.info(f"Architecture approved, stopping iterations.")
        
        return {
            **state,
            "arch_decision": arch_decision["decision"],  
        }
