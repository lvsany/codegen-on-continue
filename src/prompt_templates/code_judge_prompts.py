from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class CodeJudgePrompts:
    SYSTEM = """You are a senior Python software engineer specializing in debugging and test failure analysis.

You will be given a raw error log from automated test executions. 
Your task is to analyze raw error logs produced by automated test execution and reason about their underlying causes in the source code. 

Follow JSON schema strictly. Avoid hallucinations.
"""

    HUMAN = """Please analyze the following raw error logs from automated test executions and provide a structured error analysis along with actionable fix suggestions.

##  Instructions:

- Carefully read through the error logs and group them into distinct error categories. If multiple errors share the same root cause, group them together. If they are unrelated, list them separately.
- For each error category: Summarize the error in a clear and concise way. Identify the most likely root cause in the source code. Provide actionable modification suggestions to fix the problem.
- When providing suggestions: Point out the file/class/function that is most relevant, if it can be inferred. Suggest specific code-level changes instead of vague advice. Include minimal code snippets if they clarify the fix.

## Inputs

<Raw_Error_Logs>
{error_log}
</Raw_Error_Logs>

"""

    @staticmethod
    def get_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", CodeJudgePrompts.SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", CodeJudgePrompts.HUMAN)
        ])
    
    EXPERIENCE_SYSTEM = """You are an assistant that summarizes coding experiences from test results, feedback and code diffs.

You will receive: prev_passed (int), prev_feedbacks, cur_passed (int), curr_feedbacks, and diffs (list of {{path,diff}}).
Return a List of JSON object with fields:
- kind: 'success' or 'failure'
- scenario: short text summary of the error
- experience: good experience summarized from success to study or bad experience from failure to avoid
Rules: if cur_passed <= prev_passed, classify as 'failure' and explain why the changes didn't help and how to avoid this in future.

Follow JSON schema strictly. Avoid hallucinations.
"""

    EXPERIENCE_HUMAN = """Please summarize the coding experience based on the test results, feedbacks, and code diffs.

## Inputs

<Previous_Passed>
{prev_passed}
</Previous_Passed>

<Previous_Feedbacks>
{prev_feedback}
</Previous_Feedbacks>

<Current_Passed>
{curr_passed}
</Current_Passed>

<Current_Feedbacks>
{curr_feedback}
</Current_Feedbacks>

<Diffs>
{diffs}
</Diffs>

"""

    @staticmethod
    def get_experience_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", CodeJudgePrompts.EXPERIENCE_SYSTEM),
            # 确认是否注入历史
            # MessagesPlaceholder("history"),
            ("human", CodeJudgePrompts.EXPERIENCE_HUMAN)
        ])