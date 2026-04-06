from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

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
- Consistency with context: Ensure the generated code is consistent with already generated files (imports, function calls, shared classes, naming conventions, etc.). Use the <Context> only for reference, but do not modify them.  
- Output format: The `code` must be syntactically valid Python code and compilable. Output only the complete code for the current file. Do not include any explanatory text outside of code.  

## Inputs:

<Target_File_Skeleton>
{file_item}
</Target_File_Skeleton>

<Context>
{context}
</Context>

"""
    FIX = """The following functions are still placeholder implementations (e.g., pass or raise NotImplementedError) and must be fully implemented:
{funcs}

Please update the code by ONLY implementing these functions.
Do NOT change any other function signatures, imports, or existing implementations.
Return the full updated file code.
"""

    ITER = """Please refine and improve the complete implementation code of a file (shown in <Target_File_to_be_Modified>) based on the suggestion (shown in <Suggestion>) and contents of some code files associated with the target file (shown in <Context>).

Specifically, modify the file at {path} because the following rationale: {rationale}.

## Instructions:

- Modify only the <Target_File_to_be_Modified>.
- Implement changes strictly based on the <Suggestion>.
- Ensure consistency with the <Context> (e.g., function signatures, imports, class relationships).
- Do not introduce unrelated changes or new functions unless explicitly required by the feedback.

## Inputs:

<Target_File_to_be_Modified>
{code}
</Target_File_to_be_Modified>

<Suggestion>
{suggestion}
</Suggestion>

<Context>
{context}
</Context>
    
"""
    
    @staticmethod
    def get_system_prompt():
        return CodePrompts.SYSTEM
    
    @staticmethod
    def get_init_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", CodePrompts.INIT)
        ])
    
    @staticmethod
    def get_iter_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", CodePrompts.ITER)
        ])
    
    @staticmethod
    def get_fix_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", CodePrompts.FIX)
        ])
    

class GetFilesToUpdatePrompts:
    SYSTEM = """You are an expert software engineer responsible for planning code modifications in a multi-file software project.

Your task is to analyze feedback and decide which files should be updated, created, or removed, and in what order.
You do NOT need to modify code directly. You only need to produce a structured modification plan.

You have access to tools that can retrieve the content of any file by its path if needed. Use them ONLY when necessary.

Follow the output JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please analyze the feedback and determine which files in the project should be updated.
    
You will be given the following inputs:

- <Project_Files>: A list of all existing files in the project. Each file includes: path (the file path) and description (a short description of the file's responsibility or contents).
- <Fix_Suggestions>: Natural language feedback describing issues, missing functionality, incorrect behavior, or required changes.


## Instructions:

- Analyze the suggestions in the context of the current code.
- Identify ALL files that need to be involved in the update. This includes files directly mentioned in the suggestions or the error logs and files that contain relevant functions, classes, or imports that need to be updated.
- Only output the list of file paths that should be modified. Decide the appropriate action for each file (modify, create, or remove) and order the files in a reasonable modification sequence.
- You may request the full content of any file by calling the provided tools if the description and feedback are insufficient.


## Inputs:

<Project_Files>
{context}
</Project_Files>

<Fix_Suggestions>
{feedback}
</Fix_Suggestions>

"""

    @staticmethod
    def get_system_prompt():
        return GetFilesToUpdatePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", GetFilesToUpdatePrompts.HUMAN)
        ])