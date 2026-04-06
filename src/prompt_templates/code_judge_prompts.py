from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class CodeJudgePrompts:
    SYSTEM = """You are a senior Python software engineer specializing in debugging and test failure analysis.

You will be given a raw error log from automated test executions. 
Your task is to analyze raw error logs produced by automated test execution and reason about their underlying causes in the source code. 
Do NOT modify, rewrite, remove, or suggest changes to any test cases.

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please analyze the following raw error logs from automated test executions and provide a structured error analysis along with actionable fix suggestions.

##  Instructions:

- Carefully read through the error logs and group them into distinct error categories. If multiple errors share the same root cause, group them together. If they are unrelated, list them separately.
- For each error category: Summarize the error in a clear and concise way. Identify the most likely root cause in the source code. Provide actionable modification suggestions to fix the problem.
- When providing suggestions: Point out the file/class/function that is most relevant, if it can be inferred. Suggest specific code-level changes instead of vague advice. Include minimal code snippets if they clarify the fix.
- Do NOT modify, rewrite, remove, or suggest changes to any test cases. If the behavior of the existing code is inconsistent with the tests, the code must be changed to satisfy the tests, not the other way around.

## Inputs

<Raw_Error_Logs>
{error_log}
</Raw_Error_Logs>

"""

    @staticmethod
    def get_system_prompt():
        return CodeJudgePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", CodeJudgePrompts.HUMAN)
        ])

class ExperiencePrompts:
    SYSTEM = """You are an assistant that extracts reusable and repository-agnostic coding experiences from iterative code generation, testing feedback, and code changes.

Your goal is NOT to describe what happened in this specific repository, but to abstract general failure or success patterns that can be reused across different projects.

You will receive: test results in both the previous iteration and current iteration, and code diffs (list of {{path,diff}}).

Return a List of JSON objects with the following fields:
- kind: "success" or "failure"
- scenario: an abstract failure/success pattern describing when such issues tend to occur
- experience: a general principle or strategy that can be applied to avoid or replicate this outcome in future tasks

Rules:
- Do NOT mention any specific function names, module names, file paths, or repository-specific identifiers.
- Replace concrete details with abstract descriptions (e.g., "a function", "a module", "the package structure").
- Focus on why the change failed or succeeded structurally, not on the surface error message.
- The experience should still make sense if applied to a completely different repository.
- For failure cases: Focus on identifying ineffective or misleading modification patterns. Do NOT propose speculative future fixes unless they directly explain why the current changes failed.

Follow the JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please summarize reusable coding experience based on the progression of test results, feedback, and code modifications.

In the previous iteration, the number of passed tests was {prev_passed}.
At that stage, the main feedback indicated the following issues:

{prev_feedback}

Based on this feedback, the code was subsequently modified as shown in the diffs below.

After applying these changes, the number of passed tests increased to {curr_passed}.
The current feedback is as follows:

{curr_feedback}

Please analyze the relationship between the feedback and the corresponding code changes, and summarize generalizable coding experience that can be reused in future iterations.

Focus on lessons such as:
- what kinds of feedback typically lead to effective fixes,
- what modifications tend to improve test outcomes,
- what patterns should be avoided or reinforced in similar scenarios.

<Code_Diffs>
{diffs}
</Code_Diffs>

"""

    @staticmethod
    def get_system_prompt():
        return ExperiencePrompts.SYSTEM
    
    @staticmethod
    def get_human_prompt():
        return ChatPromptTemplate.from_messages([
            ("human", ExperiencePrompts.HUMAN)
        ])