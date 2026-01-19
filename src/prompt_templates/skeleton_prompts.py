from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

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

Follow JSON schema strictly. Avoid hallucinations.
"""

    INIT = """Please generate the initial skeleton code for a file according to the following instructions and inputs.

## Generation Instructions:

- The `skeleton_code` must be syntactically valid Python code and compilable.
- The `skeleton_code` must include import statements, global variables and constants, classes, and function signatures (with bodies replaced with `pass`).
- For function signatures, follow the parameters listed in the SSAT.
  - If a parameter has `"default": "None"`, write it as `=None` in the function signature.
  - If a parameter has another default value, use that exact default.
  - If `"default"` is missing, leave the parameter without a default.
- Add the function description as a comment immediately under each function signature.
- The imports and definitions should remain consistent with the provided previously generated skeletons.

## Inputs:

<Previously_Generated_Skeletons>
```json
{context}
```
</Previously_Generated_Skeletons>

<Target_File_SSAT>
```json
{file_item}
```
</Target_File_SSAT>
"""

# TODO: refine the ITER prompt, add instructions?
    ITER = """Please refine and improve the skeleton code of a file (shown in <Previous_Skeleton>) based on the feedback (shown in <Feedback_from_Judge>).

## Inputs:

<Previous_Skeleton>
```json
{file_item}
```
</Previous_Skeleton>

<Feedback_from_Judge>
{feedback}
</Feedback_from_Judge>

<Target_File_SSAT>
```json
{file_item}
```
</Target_File_SSAT>

<Previously_Generated_Skeletons>
```json
{context}
```
</Previously_Generated_Skeletons>

"""

    @staticmethod
    def init_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", SkeletonPrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", SkeletonPrompts.INIT)
        ])
    
    @staticmethod
    def iter_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", SkeletonPrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", SkeletonPrompts.ITER)
        ])