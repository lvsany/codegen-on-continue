from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import json
import uuid
from multiprocessing import Process
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 把src目录加到路径里，才能import workflow
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from progress_monitor import detect_current_stage, calculate_progress

app = FastAPI(title="ProjectGen Server", version="1.0.0")


def parse_cors_origins(raw_origins: str) -> List[str]:
    # 解析并清洗 CORS 白名单来源配置。
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


PROJECTGEN_CORS_ORIGINS = parse_cors_origins(
    os.getenv("PROJECTGEN_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=PROJECTGEN_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

OUTPUT_BASE_DIR = os.getenv(
    "PROJECTGEN_OUTPUT_DIR",
    os.path.join(PROJECT_ROOT, "projectgen_outputs")
)

TASK_STATUS_FILE_NAME = ".projectgen_task_status.json"

# 用字典存任务状态，这个后面要改成redis或者数据库
tasks: Dict[str, dict] = {}


def api_error(status_code: int, error_code: str, message: str, detail: Optional[Any] = None) -> HTTPException:
    # 统一构建结构化错误响应，便于前端按错误码展示。
    payload = {
        "status": status_code,
        "error_code": error_code,
        "message": message,
    }
    if detail is not None:
        payload["detail"] = detail
    return HTTPException(status_code=status_code, detail=payload)


def write_task_status_file(status_file: str, payload: Dict) -> None:
    # 将子进程执行结果写入状态文件，供主进程读取。
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def read_task_status_file(status_file: str) -> Optional[Dict]:
    # 安全读取状态文件，读取失败时返回空结果。
    if not os.path.exists(status_file):
        return None

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def sync_task_with_worker(task: Dict) -> None:
    # 同步主进程内存任务状态与子进程执行状态。
    if task["status"] in {"completed", "failed", "cancelled"}:
        return

    worker: Optional[Process] = task.get("worker_process")
    if not worker:
        return

    if worker.is_alive():
        return

    worker.join(timeout=0.1)
    task["worker_process"] = None
    task["worker_pid"] = None

    # 用户主动取消后不允许被子进程结果覆盖
    if task["status"] == "cancelled":
        return

    status_file = task.get("status_file", "")
    worker_result = read_task_status_file(status_file) if status_file else None

    if worker_result:
        task["status"] = worker_result.get("status", "failed")
        task["message"] = worker_result.get("message", "Task finished")
        task["current_stage"] = worker_result.get("current_stage", task.get("current_stage", "code"))
        task["progress"] = worker_result.get("progress", 100 if task["status"] == "completed" else task.get("progress", 0))
        task["result"] = worker_result.get("result", task.get("result", {}))
        if "error" in worker_result:
            task["error"] = worker_result["error"]
        return

    if worker.exitcode == 0:
        task["status"] = "completed"
        task["current_stage"] = "code"
        task["progress"] = 100
        task["message"] = "Generation completed successfully"
    else:
        task["status"] = "failed"
        task["error"] = f"Worker process exited with code {worker.exitcode}"
        task["message"] = "Generation failed unexpectedly"


class GenerateRequest(BaseModel):
    repo_path: str
    workspace_root: str = ""
    requirement: str = ""
    model: str = "gpt-4o"


class ProjectStatus(BaseModel):
    project_id: str
    repo_name: str
    output_dir: str
    status: str  # "pending", "running", "completed", "failed"
    current_stage: str  # "architecture", "skeleton", "code"
    iteration: int
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


@app.get("/api/health")
async def health_check():
    # 检查服务器是否正常
    # 返回服务存活状态与任务统计信息。
    return {
        "status": "healthy",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "total_tasks": len(tasks),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/projects/generate")
async def generate_project(request: GenerateRequest):
    # 创建生成任务并启动独立子进程执行工作流。
    project_id = str(uuid.uuid4())

    # 统一由服务端解析仓库路径，支持基于 workspace_root 的相对路径。
    repo_input = (request.repo_path or "").strip()
    if not repo_input:
        raise api_error(
            400,
            "INVALID_REPO_PATH",
            "repo_path 不能为空",
            {"repo_path": request.repo_path}
        )

    if os.path.isabs(repo_input):
        repo_source_dir = os.path.abspath(repo_input)
    else:
        workspace_root = (request.workspace_root or "").strip()
        base_dir = os.path.abspath(workspace_root) if workspace_root else PROJECT_ROOT
        repo_source_dir = os.path.abspath(os.path.join(base_dir, repo_input))

    # 校验仓库路径必须存在且为目录。
    if not os.path.isdir(repo_source_dir):
        raise api_error(
            404,
            "REPO_NOT_FOUND",
            "仓库路径不存在或不是目录",
            {"resolved_repo_path": repo_source_dir}
        )

    repo_name = os.path.basename(repo_source_dir.rstrip(os.sep))
    if not repo_name:
        raise api_error(
            400,
            "INVALID_REPO_PATH",
            "仓库路径非法，无法解析仓库名",
            {"resolved_repo_path": repo_source_dir}
        )

    # 路径模式下统一标记为 custom，避免旧数据集推断逻辑干扰。
    dataset = "custom"
    
    # 创建输出目录，统一写入 projectgen_outputs。
    output_base = os.path.abspath(OUTPUT_BASE_DIR)
    repo_output_dir = os.path.join(output_base, request.model, repo_name)
    os.makedirs(repo_output_dir, exist_ok=True)
    os.makedirs(os.path.join(repo_output_dir, "tmp_files"), exist_ok=True)
    
    config_path = os.path.join(repo_source_dir, "config.json")
    if not os.path.exists(config_path):
        raise api_error(
            422,
            "REPO_CONFIG_MISSING",
            "仓库缺少 config.json，无法执行生成",
            {"config_path": config_path}
        )
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            repo_config = json.load(f)
    except json.JSONDecodeError as e:
        raise api_error(
            422,
            "REPO_CONFIG_INVALID_JSON",
            "config.json 不是有效的 JSON",
            {"config_path": config_path, "line": e.lineno, "column": e.colno}
        )

    # 从仓库内文档读取输入，缺失时回退到请求参数。
    requirement = request.requirement
    prd_relative_path = repo_config.get("PRD")
    if prd_relative_path:
        prd_path = os.path.join(repo_source_dir, prd_relative_path)
        if os.path.exists(prd_path):
            with open(prd_path, "r", encoding="utf-8") as f:
                requirement = f.read()

    uml_class = ""
    uml_class_relative_path = repo_config.get("UML_class")
    if uml_class_relative_path:
        uml_class_path = os.path.join(repo_source_dir, uml_class_relative_path)
        if os.path.exists(uml_class_path):
            with open(uml_class_path, "r", encoding="utf-8") as f:
                uml_class = f.read()
    else:
        uml_candidates = repo_config.get("UML", [])
        pyreverse_candidates = [uml_file for uml_file in uml_candidates if "pyreverse" in uml_file]
        ordered_candidates = pyreverse_candidates + [uml_file for uml_file in uml_candidates if uml_file not in pyreverse_candidates]
        for uml_file in ordered_candidates:
            uml_path = os.path.join(repo_source_dir, uml_file)
            if os.path.exists(uml_path):
                with open(uml_path, "r", encoding="utf-8") as f:
                    uml_class = f.read()
                break

    arch_design = ""
    architecture_relative_path = repo_config.get("architecture_design")
    if architecture_relative_path:
        architecture_path = os.path.join(repo_source_dir, architecture_relative_path)
        if os.path.exists(architecture_path):
            with open(architecture_path, "r", encoding="utf-8") as f:
                arch_design = f.read()
    
    # 注意：与 src/main.py 保持一致，uml_sequence 传空字符串（即使读取了也不用）
    initial_state = {
        "user_input": requirement,
        "uml_class": uml_class,
        "uml_sequence": "",  # 强制为空，与原始逻辑一致
        "arch_design": arch_design,
        "repo_name": repo_name,
        "code_file_DAG": repo_config.get("code_file_DAG", []),
        "repo_dir": repo_output_dir,
        "dataset": dataset
    }
    
    # 记录任务信息
    status_file = os.path.join(repo_output_dir, "tmp_files", TASK_STATUS_FILE_NAME)

    tasks[project_id] = {
        "project_id": project_id,
        "status": "pending",
        "current_stage": "architecture",
        "iteration": 0,
        "progress": 0,
        "repo_dir": repo_output_dir,
        "dataset": dataset,
        "repo_name": repo_name,
        "output_dir": repo_output_dir,
        "status_file": status_file,
        "worker_process": None,
        "worker_pid": None,
        "created_at": datetime.now().isoformat(),
        "message": "Task created, waiting to start..."
    }

    worker_process = Process(
        target=run_workflow_process,
        args=(project_id, initial_state, status_file),
        daemon=True
    )
    worker_process.start()

    tasks[project_id]["status"] = "running"
    tasks[project_id]["message"] = "Workflow started..."
    tasks[project_id]["worker_process"] = worker_process
    tasks[project_id]["worker_pid"] = worker_process.pid
    
    return {
        "project_id": project_id,
        "repo_name": repo_name,
        "output_dir": repo_output_dir,
        "status": "running",
        "message": f"Generation task created for {repo_name}"
    }


def run_workflow_process(project_id: str, initial_state: dict, status_file: str):
    # 在独立进程中执行，可被 cancel 接口强制终止
    # 运行工作流并将结果写入状态文件。
    from workflow import build_graph

    try:
        graph = build_graph()
        print(f"[ProjectGen] Starting workflow for project {project_id}...")
        final_state = graph.invoke(initial_state, config={"recursion_limit": 50})

        write_task_status_file(status_file, {
            "status": "completed",
            "current_stage": "code",
            "progress": 100,
            "message": "Generation completed successfully",
            "result": {
            "arch_steps": final_state.get("arch_steps", 0),
            "skeleton_steps": final_state.get("skeleton_steps", 0),
            "code_steps": final_state.get("code_steps", 0)
            }
        })

    except Exception as e:
        write_task_status_file(status_file, {
            "status": "failed",
            "current_stage": "code",
            "progress": 0,
            "message": f"Generation failed: {str(e)}",
            "error": str(e)
        })


@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    # 查询任务状态，并在需要时从子进程结果同步最新状态。
    if project_id not in tasks:
        raise api_error(
            404,
            "PROJECT_NOT_FOUND",
            "任务不存在",
            {"project_id": project_id}
        )
    
    task = tasks[project_id]
    sync_task_with_worker(task)
    
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
    # 终止任务对应的子进程并更新任务状态为已取消。
    if project_id not in tasks:
        raise api_error(
            404,
            "PROJECT_NOT_FOUND",
            "任务不存在",
            {"project_id": project_id}
        )
    
    task = tasks[project_id]
    
    if task["status"] not in ["running", "pending"]:
        raise api_error(
            409,
            "PROJECT_NOT_CANCELLABLE",
            f"当前状态为 {task['status']}，无法取消",
            {"project_id": project_id, "status": task["status"]}
        )
    
    worker: Optional[Process] = task.get("worker_process")
    if worker and worker.is_alive():
        worker.terminate()
        worker.join(timeout=5)
        if worker.is_alive():
            worker.kill()
            worker.join(timeout=1)

    # 标记为已取消
    task["status"] = "cancelled"
    task["message"] = "Task terminated by user"
    task["cancelled_at"] = datetime.now().isoformat()
    task["worker_process"] = None
    task["worker_pid"] = None
    
    return {
        "project_id": project_id,
        "status": "cancelled",
        "message": "Task cancelled and worker process terminated."
    }


@app.get("/api/projects/{project_id}/files")
async def get_generated_files(
    project_id: str,
    include_content: bool = True
):
    # 按任务输出目录汇总并返回当前已生成文件列表。
    if project_id not in tasks:
        raise api_error(
            404,
            "PROJECT_NOT_FOUND",
            "任务不存在",
            {"project_id": project_id}
        )
    
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
            "output_dir": task["output_dir"],
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
            "output_dir": task["output_dir"],
            "files": [],
            "total_files": 0,
            "status": task["status"]
        }
    
    return {
        "project_id": project_id,
        "repo_name": task["repo_name"],
        "output_dir": task["output_dir"],
        "files": all_files,
        "total_files": len(all_files),
        "status": task["status"]
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "5000"))
    print("ProjectGen Server starting...")
    print(f"Output base directory: {OUTPUT_BASE_DIR}")
    print(f"Output pattern: {OUTPUT_BASE_DIR}/<model>/<repo>")
    print(f"CORS origins: {PROJECTGEN_CORS_ORIGINS}")
    print(f"Server running on http://0.0.0.0:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
