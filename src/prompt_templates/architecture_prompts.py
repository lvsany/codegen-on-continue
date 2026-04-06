from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class ArchitecturePrompts:
    SYSTEM = """You are an expert software architect assistant.

You generate SSAT (Semantic Software Architecture Tree) based on the given Product Requirement Document (PRD), UML Diagrams, and Architecture Design Document.
SSAT is a hierarchical, nested JSON tree with the following structure:
```
Module
 └── File
      ├── GlobalCode
      │    └── GlobalVariable
      │    └── GlobalBlock
      ├── Class
      │    └── Attribute
      │    └── Method
      └── Function
```
Each element contains `name` and `description` fields. `name` represents the identifier (without path), and `description` is a brief natural language summary of its responsibility.
For File elements, include a `path` field indicating the file's actual relative path from the project root.
For Function and Method elements, include a `parameters` field listing parameter specifications, which consist of `name`, `type`, and `description` (including default value info if specified in documentation).
Note: Global_functions in UML is a fake class used only to host global functions. Do not include it as a class in the SSAT; instead, move its functions to the "Functions" list.

Follow JSON schema strictly. Avoid hallucinations.
"""

    INIT = """Please generate the initial SSAT according to the following instructions and inputs.

## Extraction Instructions:

- From PRD.md: Extract descriptions of high-level modules and their responsibilities. Identify any function- or class-level behavioral descriptions.
- From UML Class Diagram: Extract all classes and their methods. Add function declarations found in the class. When available, extract function parameters including names and types.
- From UML Sequence Diagram: Capture function call chains and interactions. If parameter values are passed in interactions, infer parameter roles or examples.
- From Architecture Design Document: Extract mapping from files to modules. Capture file responsibilities and logical structure of the codebase.
- If the UML Class Diagram or UML Sequence Diagram contains elements named Global_functions (or similar), treat them as a placeholder for global functions. Do not represent them as a class in the SSAT. Instead, place the contained functions under the file's "functions" field (for global functions) or "global_code" field if they represent top-level executable code.
- When extracting function parameters, if the documentation specifies that certain parameters must have default values, **always include this information explicitly in the `description` field** of the parameter.

## Inputs:

<PRD>
{prd}
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

"""

    ITER = """Please refine and improve a previously generated SSAT (shown in <Previous_SSAT>) based on the feedback (shown in <Feedback_from_Judge>).

You are given: the previously generated SSAT, and the feedback pointing out issues, omissions, or inconsistencies.

Other reference documents (e.g., PRD, UML Class Diagram, UML Sequence Diagram, Architecture Design Document) are NOT directly provided in this prompt.
If and only if the feedback or the current SSAT requires verification, clarification, or additional details from these documents, you may call the appropriate tool to retrieve the needed information.

Do NOT blindly re-extract all information. Focus on minimal, targeted modifications that address the feedback.
    
## Inputs:

<Previous_SSAT>
{latest_arch}
</Previous_SSAT>

<Feedback_from_Judge>
{feedback}
</Feedback_from_Judge>

"""
    
    @staticmethod
    def get_system_prompt():
        return ArchitecturePrompts.SYSTEM
    
    @staticmethod
    def get_init_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", ArchitecturePrompts.INIT)
        ])
    
    @staticmethod
    def get_iter_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", ArchitecturePrompts.ITER)
        ])