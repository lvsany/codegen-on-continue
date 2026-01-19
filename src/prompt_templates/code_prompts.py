from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class CodePrompts:
    SYSTEM = """You are an expert software project code generator.

Your task is to generate the full implementation code for a single file, based on its provided skeleton and the context of already generated files. 
All occurrences of `pass` in the provided skeleton are placeholders and MUST be fully replaced with concrete, executable Python code. No `pass` statements should remain in the final output.

Follow JSON schema strictly. Avoid hallucinations.
"""

    INIT = """Please generate the complete implementation code for a file according to the following instructions and inputs.

## Generation Instructions:

- Strict adherence to skeleton: Do not add new functions, classes, or methods that are not present in the skeleton. Do not remove or rename any existing functions, classes, or methods. Preserve the order and structure exactly as given.  
- Function implementation: Replace `pass` with the correct implementation according to the function name, parameters, and descriptions provided in the skeleton. Keep the function-level doc/comment (description) directly under the function signature.  
- Consistency with context: Ensure the generated code is consistent with already generated files (imports, function calls, shared classes, naming conventions, etc.). Use the <Previously_Generated_Files> only for reference, but do not modify them.  
- Output format: The `code` must be syntactically valid Python code and compilable. Output only the complete code for the current file. Do not include any explanatory text outside of code.  

## Inputs:

<Target_File_Skeleton>
```json
{file_item}
```
</Target_File_Skeleton>

<Previously_Generated_Files>
```json
{context}
```
</Previously_Generated_Files>

"""

    ITER = """Please refine and improve the complete implementation code of a file (shown in <Target_File_to_be_Modified>) based on the feedback (shown in <Test_Feedback_Suggestions>).

You will be given the following inputs:

- <Target_File_to_be_Modified>: Provided as JSON with `"path"` and `"code"` fields.
- <Test_Feedback_Suggestions>: Natural language feedback summarizing the errors and proposed fixes, which should guide the modifications.
- <Context_Files>: A list of other already generated project files, each given as JSON with `"path"` and `"code"` fields. These should be considered for consistency, but do not modify them.
- <History>: A list of previous interactions, including the initial prompt and any feedback from the judge.

## Instructions:

- Modify only the <Target_File_to_be_Modified>.
- Implement changes strictly based on the <Test_Feedback_Suggestions>.
- Ensure consistency with the <Context_Files> (e.g., function signatures, imports, class relationships).
- Do not introduce unrelated changes or new functions unless explicitly required by the feedback.
- Maintain Python best practices and correctness.


## Inputs:

<Target_File_to_be_Modified>
```json
{file_item}
```
</Target_File_to_be_Modified>

<Test_Feedback_Suggestions>
{feedback}
</Test_Feedback_Suggestions>

<Context_Files>
```json
{context}
```
</Context_Files>

<History>
{history_str}
</History>
    
"""

    @staticmethod
    def init_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", CodePrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", CodePrompts.INIT)
        ])
    
    @staticmethod
    def iter_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", CodePrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", CodePrompts.ITER)
        ])
    

class GetFilesToUpdatePrompts:
    SYSTEM = """You are an expert software project code generator.
    
Your task is to identify which files need to be modified based on the provided feedback and the current project code.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please analyze the provided code modification suggestions and determine which files in the current project code need to be modified to address the issues.
    
You will be given the following inputs:

- <Current_Project_Code>: Each file is represented as an object with `"path"` and `"code"` fields.
- <Fix_Suggestions>: Natural language suggestions detailing the issues and proposed fixes.


## Instructions:

- Analyze the suggestions in the context of the current code.
- Identify which files must be modified to address the issues. This includes files directly mentioned in the suggestions or the error logs and files that contain relevant functions, classes, or imports that need to be updated.
- Only output the list of file paths that should be modified.


## Inputs:

<Current_Project_Code>
```json
{context}
```
</Current_Project_Code>

<Fix_Suggestions>
{feedback}
</Fix_Suggestions>

"""

    @staticmethod
    def get_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", GetFilesToUpdatePrompts.SYSTEM),
            # MessagesPlaceholder("history"),
            ("human", GetFilesToUpdatePrompts.HUMAN)
        ])