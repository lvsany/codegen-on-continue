from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class ArchJudgePrompts:
    SYSTEM = """You are an expert software architecture reviewer.

Your task is to evaluate the quality of a Semantic Software Architecture Tree (SSAT) for a software project. 
You do **not** have direct access to the full PRD, UML diagrams, or Architecture Design Document.
Instead, you can use the provided tools to query relevant information on demand. 
Tools are OPTIONAL, not mandatory. Only call a tool if the required information is NOT already present in the SSAT or cannot be reasonably inferred from the provided input. Do NOT call tools for confirmation, redundancy, or curiosity.

You can use the following tools:

- get_requirement(): Retrieve the project requirement information, including the UML class diagram and the architecture design document. Use this tool when you need to understand the system structure, expected modules, or implementation requirements before generating or verifying code.
- get_diff_with_previous_ssat(): Returns differences compared to the previous SSAT.
- check_ssat_structure(): Validates the SSAT against structural rules.
- check_interface_completeness(): Checks whether SSAT interfaces match UML definitions.
- search_docs_by_keyword(query: str, top_k: int = 5): Searches for relevant content in documents by keyword.
- find_missing_files(): Identify Python files that are defined in the architecture design directory tree but missing from the SSAT file structure.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please evaluate the SSAT based on the following criteras and instructions, and give some suggestions for refinement.
You must rely on the tools to query any information you need; do not assume or hallucinate document contents.

## Criterias:  

- Requirement Coverage: Does the SSAT cover all the functional modules mentioned in the requirements?  
- Consistency with Provided Information: Does the SSAT faithfully follow the directory structure, file names, and function names explicitly given in the PRD, UML diagrams, and Architecture Design Document?
- Interface Consistency: Are the interface names clear, unambiguous, and free from redundancy?  
- Dependency Relations: Are there any circular dependencies? Does the dependency structure follow common layered SSAT principles?  

## Instructions:

- For each criterion, give a score between 1 (poor) and 10 (excellent), and provide a concise justification.
- Provide a final overall score between 1 and 10 based on the combined evaluation.
- The decision field is a mandatory review gate: choose "approve" ONLY if the SSAT can proceed to the next stage; choose "reject" if any file require redesign before continuation.
- Use the tools to retrieve any relevant information from the documents. Do not assume any information that is not explicitly provided or retrievable.
- Only call a tool if the required information is NOT already present in the SSAT or cannot be reasonably inferred from the provided input. Do NOT call tools for confirmation, redundancy, or curiosity.
- Prioritize consistency with the provided information over general design principles.
- Do not generate or suggest test files.

## Concrete Suggestions Requirement

Your suggestions must be specific and actionable.
When tools report missing or inconsistent components, you must explicitly list them rather than giving general advice.
For example:

GOOD suggestions:

- Add the missing file policy_generator.py defined in the Architecture Design.
- Add class Record in cloudtrail.py as defined in the UML class diagram.
- Implement function generate_policy() in policy_generator.py.
- Add module record_sources/local_directory_record_source.py.

BAD suggestions (do NOT produce these):

- Include missing files.
- Ensure all interfaces are implemented.
- Improve requirement coverage.

If the tools identify missing components, your suggestions should include:

- Missing files to add: <file_path>
- Missing classes or interfaces: <class_name> in <file_path>
- Missing functions: <function_name> in <file_path>

## Inputs:

<SSAT>
{architecture}
</SSAT>

"""
    
    @staticmethod
    def get_system_prompt():
        return ArchJudgePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        # return ArchJudgePrompts.HUMAN
        return ChatPromptTemplate.from_messages([
            ("human", ArchJudgePrompts.HUMAN)
        ])