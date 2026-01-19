from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class ArchJudgePrompts:
    SYSTEM = """You are an expert software architecture reviewer.

You will be given: Product Requirement Document (PRD), UML Diagrams, Architecture Design Document, and a Semantic Software Architecture Tree (SSAT).
Your task is to evaluate the quality of the SSAT based on the following four criteria: Requirement Coverage, Consistency with Provided Information, Interface Consistency, and Dependency Relations.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please evaluate the SSAT based on the following criteras and instructions.

## Criterias:  

- Requirement Coverage: Does the SSAT cover all the functional modules mentioned in the requirements?  
- Consistency with Provided Information: Does the SSAT faithfully follow the directory structure, file names, and function names explicitly given in the PRD, UML diagrams, and Architecture Design Document?
- Interface Consistency: Are the interface names clear, unambiguous, and free from redundancy?  
- Dependency Relations: Are there any circular dependencies? Does the dependency structure follow common layered SSAT principles?  

## Instructions:

- For each criterion, give a score between 1 (poor) and 10 (excellent), and provide a short justification of your evaluation. 
- Give a final overall score for the SSAT between 1 (poor) and 10 (excellent*, based on how well it satisfies the four detialed criterias.
- If the PRD, UML diagrams, or Architecture Design Document explicitly provide a file directory structure, file names, or function names, you must prioritize consistency with this given information over general design principles. Do not suggest changes that contradict explicitly provided structures or names merely for abstract notions of modularity or cohesion. Your evaluation should respect and align with the provided information as the highest authority.
- Do not suggest or generate any test files as part of the evaluation or revision.


## Inputs:

<PRD>
{requirement}
</PRD>

<UML_Class_Diagram>
{uml_class} 
</UML_Class_Diagram>

<UML_Sequence_Diagram>
{uml_sequence}
</UML_Sequence_Diagram>

<Architecture_Design_Document>
{arch_design}
</Architecture_Design_Document>

<SSAT>
{architecture}
</SSAT>

"""

    @staticmethod
    def get_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", ArchJudgePrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", ArchJudgePrompts.HUMAN)
        ])