from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class SkeletonJudgePrompts:
    SYSTEM = """You are an expert software code reviewer.

You will be given: a Semantic Software Architecture Tree (SSAT), and the generated skeleton code.
Your task is to evaluate the quality of the generated skeleton code, and provide actionable modification suggestions with exact file paths.

You can use the following tools:

- check_ssat_skeleton_coverage(): Checks if the skeleton code covers all files, classes and functions specified in the SSAT.
- search_docs_by_keyword(query: str, top_k: int = 5): Searches for relevant content in documents by keyword.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please evaluate the skeleton code based on the following criteras and instructions.

## Criterias:

- Directory Structure Matching: Does the skeleton's directory and file hierarchy match the SSAT specification? Are there missing or extra files/directories? Is the nesting consistent with the design?
- Interface & Call Relationship Matching: Do the classes and functions (including names, parameters, and default values) align with the SSAT definition? Are all expected interfaces present? Are there inconsistencies or omissions?

## Instructions:

- For each criterion, give a score between 1 (poor) and 10 (excellent), and provide a short justification of your evaluation. 
- Give a final overall score for the SSAT between 1 (poor) and 10 (excellent), based on how well it satisfies the two detailed criterias.
- The decision field is a mandatory review gate: choose "approve" ONLY if the SSAT can proceed to the next stage without major architectural rework; choose "reject" if any critical issues require redesign before continuation.
- You MUST provide a list of required modifications. For each modification, specify:
  - `path`: the file path that needs to be modified or created
  - `suggestion`: a concrete modification instruction (e.g., add/remove/rename a class, function, or file)

## Inputs:

<SSAT>
{architecture}
</SSAT>

<Skeleton_Code>
{skeleton}
</Skeleton_Code>

"""

    @staticmethod
    def get_system_prompt():
        return SkeletonJudgePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", SkeletonJudgePrompts.HUMAN)
        ])