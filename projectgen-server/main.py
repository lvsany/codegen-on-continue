from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

# 把src目录加到路径里，才能import workflow
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from progress_monitor import detect_current_stage, calculate_progress

app = FastAPI(title="ProjectGen Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATASET_BASE_DIR = os.getenv(
    "PROJECTGEN_DATASET_DIR", 
    os.path.join(PROJECT_ROOT, "datasets")
)

# 线程池，可以设置同时跑几个任务
executor = ThreadPoolExecutor(max_workers=3)

# 用字典存任务状态，这个后面要改成redis或者数据库
tasks: Dict[str, dict] = {}


class GenerateRequest(BaseModel):
    dataset: str
    repo_name: str
    requirement: str
    uml_class: str = ""
    uml_sequence: str = ""
    arch_design: str = ""
    model: str = "gpt-4o"
    code_file_DAG: List[str] = []


class ProjectStatus(BaseModel):
    project_id: str
    status: str  # "pending", "running", "completed", "failed"
    current_stage: str  # "architecture", "skeleton", "code"
    iteration: int
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


@app.get("/api/health")
async def health_check():
    # 检查服务器是否正常
    return {
        "status": "healthy",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "total_tasks": len(tasks),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/projects/generate")
async def generate_project(request: GenerateRequest):
    project_id = str(uuid.uuid4())
    
    # 先检查这个repo存不存在
    repo_source_dir = os.path.join(DATASET_BASE_DIR, request.dataset, request.repo_name)
    if not os.path.exists(repo_source_dir):
        raise HTTPException(404, f"Repository not found: {repo_source_dir}")
    
    # 创建输出目录，路径格式和src/main.py保持一致
    output_base = os.path.join(PROJECT_ROOT, f"{request.dataset}_outputs")
    repo_output_dir = os.path.join(output_base, request.model, request.repo_name)
    os.makedirs(repo_output_dir, exist_ok=True)
    os.makedirs(os.path.join(repo_output_dir, "tmp_files"), exist_ok=True)
    
    config_path = os.path.join(repo_source_dir, "config.json")
    if not os.path.exists(config_path):
        raise HTTPException(404, f"config.json not found in {repo_source_dir}")
    
    with open(config_path) as f:
        repo_config = json.load(f)
    
    initial_state = {
        "user_input": request.requirement,
        "uml_class": request.uml_class,
        "uml_sequence": request.uml_sequence,
        "arch_design": request.arch_design,
        "repo_name": request.repo_name,
        "code_file_DAG": repo_config.get("code_file_DAG", []),
        "repo_dir": repo_output_dir,
        "dataset": request.dataset
    }
    
    # 记录任务信息
    tasks[project_id] = {
        "project_id": project_id,
        "status": "pending",
        "current_stage": "architecture",
        "iteration": 0,
        "progress": 0,
        "repo_dir": repo_output_dir,
        "dataset": request.dataset,
        "repo_name": request.repo_name,
        "created_at": datetime.now().isoformat(),
        "message": "Task created, waiting to start..."
    }
    
    # 扔到后台线程去跑
    executor.submit(run_workflow_sync, project_id, initial_state)
    
    return {
        "project_id": project_id,
        "status": "pending",
        "message": f"Generation task created for {request.repo_name}"
    }


def run_workflow_sync(project_id: str, initial_state: dict):
    # 这个函数在后台线程里跑，会一直卡住直到生成完
    from workflow import build_graph
    
    try:
        tasks[project_id]["status"] = "running"
        tasks[project_id]["message"] = "Workflow started..."
        
        # 调用原来的workflow代码
        graph = build_graph()
        final_state = graph.invoke(initial_state)
        
        # 跑完了，更新状态
        tasks[project_id]["status"] = "completed"
        tasks[project_id]["current_stage"] = "code"
        tasks[project_id]["progress"] = 100
        tasks[project_id]["message"] = "Generation completed successfully"
        tasks[project_id]["result"] = {
            "arch_steps": final_state.get("arch_steps", 0),
            "skeleton_steps": final_state.get("skeleton_steps", 0),
            "code_steps": final_state.get("code_steps", 0)
        }
        
    except Exception as e:
        tasks[project_id]["status"] = "failed"
        tasks[project_id]["error"] = str(e)
        tasks[project_id]["message"] = f"Generation failed: {str(e)}"


@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    
    if task["status"] == "running":
        repo_dir = task["repo_dir"]
        stage, iteration = detect_current_stage(repo_dir)
        
        task["current_stage"] = stage
        task["iteration"] = iteration
        task["progress"] = calculate_progress(stage, iteration)
    
    return ProjectStatus(**task)


@app.get("/api/projects/{project_id}/files")
async def get_generated_files(project_id: str):
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    
    if task["status"] != "completed":
        raise HTTPException(400, "Project not completed yet")
    
    repo_dir = task["repo_dir"]
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    files = []
    code_files = [f for f in os.listdir(tmp_dir) if f.startswith("generated_code_")]
    if not code_files:
        return {"files": []}
    
    latest_code_file = sorted(code_files)[-1]
    code_jsonl_path = os.path.join(tmp_dir, latest_code_file)
    
    with open(code_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            files.append({
                "path": item.get("path", ""),
                "content": item.get("content", "")
            })
    
    return {
        "project_id": project_id,
        "repo_name": task["repo_name"],
        "files": files,
        "total_files": len(files)
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "5000"))
    print("ProjectGen Server starting...")
    print(f"Dataset directory: {DATASET_BASE_DIR}")
    print(f"Output pattern: {PROJECT_ROOT}/<dataset>_outputs/<model>/<repo>")
    print(f"Server running on http://0.0.0.0:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
