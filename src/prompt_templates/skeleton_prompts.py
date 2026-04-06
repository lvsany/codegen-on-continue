from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class SkeletonPrompts:
    SYSTEM = """You are an expert software project code generator.
    
Your task is to generate the skeleton code (with function bodies replaced with `pass`) for a single file based on its SSAT (Semantic Software Architecture Tree) description, while ensuring consistency with already generated files.
The SSAT of a code file is a hierarchical, nested JSON tree with the following structure:
```
File
 ├── GlobalCode
 │    └── GlobalVariable
 │    └── GlobalBlock
 ├── Class
 │    └── Attribute
 │    └── Method
 └── Function
```
Each element contains `name` and `description` fields. `name` represents the identifier (without path), and `description` is a brief natural language summary of its responsibility.
File elements include a `path` field indicating the file's actual relative path from the project root.
Function and Method elements include a `parameters` field listing parameter specifications, which consist of `name`, `type`, and `description` (including default value info if specified in documentation).

IMPORTANT CONTEXT RULES:
- You are NOT provided with the full project context upfront.
- You may need information about other files (their SSAT or skeleton) to ensure consistency.
- You MUST actively retrieve such information using the provided tools when needed.
- Do NOT assume missing information. If consistency with another file is required, query it explicitly via tools.
- You MAY first call `flatten_ssat_symbols` to get a project-wide overview of files and symbols. If details of a specific file are required, use `find_ssat_of_file_by_path` for its SSAT structure, and `find_skeleton_of_file_by_path` for its generated skeleton.

Follow JSON schema strictly. Avoid hallucinations.
"""

    INIT = """Please generate the initial skeleton code for the file at {path} according to the following instructions and inputs.

## Generation Instructions:

- The `skeleton_code` must be syntactically valid Python code and compilable.
- The `skeleton_code` must include import statements, global variables and constants, classes, and function signatures (with bodies replaced with `pass`).
- For function signatures, follow the parameters listed in the SSAT.
  - If a parameter has `"default": "None"`, write it as `=None` in the function signature.
  - If a parameter has another default value, use that exact default.
  - If `"default"` is missing, leave the parameter without a default.
- Add the function description as a comment immediately under each function signature.
- The imports and definitions should remain consistent with the provided previously generated skeletons.
- No complete project context is provided directly. If imports, references, base classes, or consistency with other files are required, use the available tools to retrieve the SSAT or skeleton of the corresponding files by path.

## Inputs:

<Target_File_SSAT>
{file_ssat}
</Target_File_SSAT>
"""

    ITER = """Please refine and improve the skeleton code of a file (shown in <Target_File_Previous_Skeleton>) based on the suggestion (shown in <Suggestion>) and its SSAT (shown in <Target_File_SSAT>).

Specifically, {action} the file at {path} because the following rationale: {rationale}.

## Inputs:

<Target_File_Previous_Skeleton>
{previous_file_skeleton}
</Target_File_Previous_Skeleton>

<Suggestion>
{suggestion}
</Suggestion>

<Target_File_SSAT>
{file_ssat}
</Target_File_SSAT>

"""
    @staticmethod
    def get_system_prompt():
        return SkeletonPrompts.SYSTEM
    
    @staticmethod
    def get_init_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", SkeletonPrompts.INIT)
        ])
    
    @staticmethod
    def get_iter_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", SkeletonPrompts.ITER)
        ])
        
        
class GetSkeletonFilesToUpdatePrompts:
    SYSTEM = """You are an expert software project code generator.

Your task is to determine which skeleton files need to be modified, and how they should be modified, based on judge feedback and the current SSAT and skeleton state.

You may use tools to retrieve additional structural information when needed.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please analyze the suggested changes of the feedback from judge, and determine how to update the project skeleton accordingly.

## Instructions:

- Analyze the suggested changes carefully.
- Determine which skeleton files need to be modified, created, or removed.
- If additional structural details are required, use tools to retrieve the SSAT or skeleton of specific files. Do NOT assume missing structure without verification via tools.

## Output Requirements:

- Output a list of files to update.
- For each file, provide:
  - `path`: file path
  - `action`: one of [modify, create, remove]
  - `rationale`: concise explanation of why this file needs to be updated
  - `suggestion`: a brief description of what should be changed in this file

## Inputs:

<Suggested_Changes>
{suggested_changes}
</Suggested_Changes>

"""
    @staticmethod
    def get_system_prompt():
        return GetSkeletonFilesToUpdatePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", GetSkeletonFilesToUpdatePrompts.HUMAN)
        ])