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


def find_repo_in_datasets(repo_name: str) -> Optional[str]:
    """在所有数据集目录中递归搜索仓库"""
    if not os.path.exists(DATASET_BASE_DIR):
        return None
    
    for dataset in os.listdir(DATASET_BASE_DIR):
        dataset_path = os.path.join(DATASET_BASE_DIR, dataset)
        if not os.path.isdir(dataset_path):
            continue
        
        repo_path = os.path.join(dataset_path, repo_name)
        if os.path.exists(repo_path) and os.path.isdir(repo_path):
            print(f"[ProjectGen] Found {repo_name} in dataset: {dataset}")
            return dataset
    
    return None


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
    
    # 如果没有指定数据集或数据集为空，自动搜索
    if not request.dataset or request.dataset == "":
        print(f"[ProjectGen] No dataset specified, searching for {request.repo_name}...")
        found_dataset = find_repo_in_datasets(request.repo_name)
        if not found_dataset:
            raise HTTPException(404, f"Repository '{request.repo_name}' not found in any dataset")
        dataset = found_dataset
        print(f"[ProjectGen] Using dataset: {dataset}")
    else:
        dataset = request.dataset
    
    # 检查这个repo存不存在
    repo_source_dir = os.path.join(DATASET_BASE_DIR, dataset, request.repo_name)
    if not os.path.exists(repo_source_dir):
        raise HTTPException(404, f"Repository not found: {repo_source_dir}")
    
    # 创建输出目录，路径格式和src/main.py保持一致
    output_base = os.path.join(PROJECT_ROOT, f"{dataset}_outputs")
    repo_output_dir = os.path.join(output_base, request.model, request.repo_name)
    os.makedirs(repo_output_dir, exist_ok=True)
    os.makedirs(os.path.join(repo_output_dir, "tmp_files"), exist_ok=True)
    
    config_path = os.path.join(repo_source_dir, "config.json")
    if not os.path.exists(config_path):
        raise HTTPException(404, f"config.json not found in {repo_source_dir}")
    
    with open(config_path) as f:
        repo_config = json.load(f)
    
    # 与 src/main.py 完全一致：从 dataset 目录读取文件，而不是使用前端传递的数据
    requirement = open(os.path.join(repo_source_dir, repo_config['PRD']), "r").read()
    
    if dataset == 'DevBench':
        uml_class = open(os.path.join(repo_source_dir, repo_config['UML_class']), "r").read()
        uml_sequence = open(os.path.join(repo_source_dir, repo_config['UML_sequence']), "r").read()
    elif dataset == 'CodeProjectEval':
        # CodeProjectEval 使用 UML 数组，选择 pyreverse 版本
        uml_class = ""
        for uml_file in repo_config.get('UML', []):
            if 'pyreverse' in uml_file:
                uml_class = open(os.path.join(repo_source_dir, uml_file), "r").read()
                break
        uml_sequence = ""
    else:
        # 其他数据集的默认处理
        uml_class = request.uml_class
        uml_sequence = request.uml_sequence
        requirement = request.requirement
    
    arch_design = open(os.path.join(repo_source_dir, repo_config['architecture_design']), "r").read()
    
    # 注意：与 src/main.py 保持一致，uml_sequence 传空字符串（即使读取了也不用）
    initial_state = {
        "user_input": requirement,
        "uml_class": uml_class,
        "uml_sequence": "",  # 强制为空，与原始逻辑一致
        "arch_design": arch_design,
        "repo_name": request.repo_name,
        "code_file_DAG": repo_config.get("code_file_DAG", []),
        "repo_dir": repo_output_dir,
        "dataset": dataset
    }
    
    # 记录任务信息
    tasks[project_id] = {
        "project_id": project_id,
        "status": "pending",
        "current_stage": "architecture",
        "iteration": 0,
        "progress": 0,
        "repo_dir": repo_output_dir,
        "dataset": dataset,
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
    import threading
    
    try:
        # 检查是否已被取消
        if tasks[project_id]["status"] == "cancelled":
            return
            
        tasks[project_id]["status"] = "running"
        tasks[project_id]["message"] = "Workflow started..."
        
        # 调用原来的workflow代码
        graph = build_graph()
        
        # 注意：graph.invoke() 是阻塞调用，无法在运行中中断
        # 取消操作只能在下次迭代前生效
        # TODO: 需要修改 workflow 内部以支持中断检查
        print(f"[ProjectGen] Starting workflow for project {project_id}...")
        final_state = graph.invoke(initial_state, config={"recursion_limit": 50})
        
        # 检查是否在运行期间被取消
        if tasks[project_id]["status"] == "cancelled":
            tasks[project_id]["message"] = "Generation cancelled during execution"
            return
        
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
        # 检查是否因为取消而引发的异常
        if tasks[project_id]["status"] == "cancelled":
            tasks[project_id]["message"] = f"Generation cancelled: {str(e)}"
        else:
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


@app.post("/api/projects/{project_id}/cancel")
async def cancel_project(project_id: str):
    """取消正在运行的项目生成任务"""
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    
    if task["status"] not in ["running", "pending"]:
        return {
            "project_id": project_id,
            "message": f"Task is already {task['status']}, cannot cancel"
        }
    
    # 标记为已取消
    task["status"] = "cancelled"
    task["message"] = "Task cancelled by user"
    task["cancelled_at"] = datetime.now().isoformat()
    
    return {
        "project_id": project_id,
        "status": "cancelled",
        "message": "Task cancellation requested. The task will stop at the next checkpoint."
    }


@app.get("/api/projects/{project_id}/files")
async def get_generated_files(project_id: str, include_content: bool = True):
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    repo_dir = task["repo_dir"]
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    all_files = []
    
    # 检查 tmp_files 目录是否存在
    if not os.path.exists(tmp_dir):
        print(f"[ProjectGen] tmp_dir not exists: {tmp_dir}")
        return {
            "project_id": project_id,
            "repo_name": task["repo_name"],
            "files": [],
            "total_files": 0,
            "status": task["status"]
        }
    
    try:
        # 1. 获取架构文件 (支持 arch_step_* 和 architecture_* 两种命名)
        arch_files = sorted([f for f in os.listdir(tmp_dir) if f.startswith("arch_step_") or f.startswith("architecture_")])
        print(f"[ProjectGen] 找到 {len(arch_files)} 个架构文件")
        for arch_file in arch_files:
            file_path = os.path.join(tmp_dir, arch_file)
            if os.path.exists(file_path):
                file_info = {"path": f"tmp_files/{arch_file}"}
                if include_content:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_info["content"] = f.read()
                    except Exception as e:
                        print(f"[ProjectGen] 读取文件失败 {arch_file}: {e}")
                        file_info["content"] = ""
                all_files.append(file_info)
        
        # 2. 获取骨架文件 (支持 skeleton_step_* 和 skeleton_* 两种命名)
        skeleton_files = sorted([f for f in os.listdir(tmp_dir) if f.startswith("skeleton_step_") or (f.startswith("skeleton_") and not f.startswith("skeleton_step_"))])
        print(f"[ProjectGen] 找到 {len(skeleton_files)} 个骨架文件")
        for skeleton_file in skeleton_files:
            file_path = os.path.join(tmp_dir, skeleton_file)
            if os.path.exists(file_path):
                file_info = {"path": f"tmp_files/{skeleton_file}"}
                if include_content:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_info["content"] = f.read()
                    except Exception as e:
                        print(f"[ProjectGen] 读取文件失败 {skeleton_file}: {e}")
                        file_info["content"] = ""
                all_files.append(file_info)
        
        # 3. 获取生成的代码文件
        code_files = sorted([f for f in os.listdir(tmp_dir) if f.startswith("generated_code_")])
        print(f"[ProjectGen] 找到 {len(code_files)} 个代码文件")
        if code_files:
            # 使用最新的代码文件
            latest_code_file = code_files[-1]
            code_jsonl_path = os.path.join(tmp_dir, latest_code_file)
            
            if os.path.exists(code_jsonl_path):
                try:
                    with open(code_jsonl_path, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                item = json.loads(line)
                                file_info = {"path": item.get("path", "")}
                                if include_content:
                                    file_info["content"] = item.get("content", "")
                                all_files.append(file_info)
                            except json.JSONDecodeError as e:
                                print(f"[ProjectGen] JSON解析失败: {e}")
                                continue
                except Exception as e:
                    print(f"[ProjectGen] 读取代码文件失败: {e}")
        
        print(f"[ProjectGen] 总共返回 {len(all_files)} 个文件")
        
    except Exception as e:
        print(f"[ProjectGen] 获取文件列表失败: {e}")
        return {
            "project_id": project_id,
            "repo_name": task["repo_name"],
            "files": [],
            "total_files": 0,
            "status": task["status"]
        }
    
    return {
        "project_id": project_id,
        "repo_name": task["repo_name"],
        "files": all_files,
        "total_files": len(all_files),
        "status": task["status"]
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "5000"))
    print("ProjectGen Server starting...")
    print(f"Dataset directory: {DATASET_BASE_DIR}")
    print(f"Output pattern: {PROJECT_ROOT}/<dataset>_outputs/<model>/<repo>")
    print(f"Server running on http://0.0.0.0:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
