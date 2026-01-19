from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class SkeletonJudgePrompts:
    SYSTEM = """You are an expert software code reviewer.

You will be given: a Semantic Software Architecture Tree (SSAT), and the generated skeleton code.
Your task is to evaluate the quality of the generated skeleton code based on the following two criteria: Directory Structure Matching, Interface & Call Relationship Matching.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please evaluate the skeleton code based on the following criteras and instructions.

## Criterias:

- Directory Structure Matching: Does the skeleton's directory and file hierarchy match the SSAT specification? Are there missing or extra files/directories? Is the nesting consistent with the design?
- Interface & Call Relationship Matching: Do the classes and functions (including names, parameters, and default values) align with the SSAT definition? Are all expected interfaces present? Are there inconsistencies or omissions?

## Instructions:

- For each criterion, give a score between 1 (poor) and 10 (excellent), and provide a short justification of your evaluation. 
- Give a final overall score for the SSAT between 1 (poor) and 10 (excellent*, based on how well it satisfies the four detialed criterias.


## Inputs:

<SSAT>
```json
{architecture}
```
</SSAT>

<Skeleton_Code>
```json
{skeleton}
```
</Skeleton_Code>

"""

    @staticmethod
    def get_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", SkeletonJudgePrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", SkeletonJudgePrompts.HUMAN)
        ])