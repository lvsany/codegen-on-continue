from langgraph.graph import StateGraph, END
from agents.architecture_agent import ArchitectureAgent
from agents.arch_judge_agent import ArchJudgeAgent
from agents.skeleton_agent import SkeletonAgent
from agents.skeleton_judge_agent import SkeletonJudgeAgent
from agents.code_agent import CodeAgent
from agents.code_judge_agent import CodeJudgeAgent
from langchain_openai import ChatOpenAI
import os
from langchain_deepseek import ChatDeepSeek


os.environ["OPENAI_API_KEY"] = ''

llm = ChatOpenAI(
    model_name="gpt-5", 
    temperature=0, 
    base_url="https://api.openai.com/v1",
    response_format={"type": "json_object"}
)

second_llm = ChatOpenAI(
    model_name="gpt-5", 
    temperature=0.8, 
    base_url="https://api.openai.com/v1",
    response_format={"type": "json_object"}
)

architecture_agent = ArchitectureAgent(llm=llm)  
arch_judge_agent = ArchJudgeAgent(llm=llm)          
arch_judge_agent.MAX_ARCH_ITER = 3               


skeleton_agent = SkeletonAgent(llm=llm)
skeleton_judge_agent = SkeletonJudgeAgent(llm=llm)
skeleton_judge_agent.MAX_SKELETON_ITER = 3

code_agent = CodeAgent(llm=llm)       
code_agent.CONTEXT_MAX_LENGTH = 5 
code_judge_agent = CodeJudgeAgent(llm=second_llm)
code_judge_agent.MAX_CODE_ITER = 10
code_judge_agent.TEST_BASE_DIR = "../datasets/"

def route_arch_judge(state: dict) -> str:
    return "skeleton" if state.get("arch_decision") == "approve" else "architecture"

def route_skeleton_judge(state: dict) -> str:
    return "code" if state.get("skeleton_decision") == "approve" else "skeleton"

def route_code_judge(state: dict) -> str:
    return END if state.get("code_decision") == "approve" else "code"

def build_graph():
    builder = StateGraph(dict)

    builder.add_node("architecture", architecture_agent)
    builder.add_node("arch_judge", arch_judge_agent)
    
    builder.add_node("skeleton", skeleton_agent)
    builder.add_node("skeleton_judge", skeleton_judge_agent)
    
    builder.add_node("code", code_agent)
    builder.add_node("code_judge", code_judge_agent)

    builder.set_entry_point("architecture")
    builder.add_edge("architecture", "arch_judge")
    builder.add_conditional_edges("arch_judge", route_arch_judge)

    builder.add_edge("skeleton", "skeleton_judge")
    builder.add_conditional_edges("skeleton_judge", route_skeleton_judge)
    
    builder.add_edge("code", "code_judge")
    builder.add_conditional_edges("code_judge", route_code_judge)

    return builder.compile()