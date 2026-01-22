# ProjectGen × Continue "套壳"集成方案

**版本**: 6.0 (修订版，修复问题)  
**日期**: 2026年1月22日  
**核心理念**: Continue 只提供聊天界面，ProjectGen 核心代码(src/)完全不动

---

## ⚠️ 重要修订说明

本版本修复了以下问题：
1. 修正了项目路径（`new-projectgen` → `codegen-on-continue`）
2. 修正了 TypeScript 代码中的接口类型问题
3. 补充了 config.json 中文件路径的正确解析逻辑
4. 增加了 AbortController 支持和更完善的错误处理
5. 修正了 Continue SDK 的正确用法（`fetch` 从参数解构获取）

---

## 💡 核心思想：什么是"套壳"？

### 简单来说

想象一下：
- **Continue** = 一个漂亮的聊天窗口 + 能读写文件的助手
- **ProjectGen** = 你已经写好的代码生成引擎 (在 src/ 目录里)
- **我们要做的** = 让 Continue 这个聊天窗口能调用 ProjectGen 引擎

**类比**：就像给一辆车换了个新的仪表盘，但发动机还是原来那个。

### 为什么这样做？

1. ✅ **src/ 目录完全不需要改动** - 你的 workflow.py、agents/ 都保持原样
2. ✅ **利用 Continue 的界面** - 有现成的聊天窗口、进度显示
3. ✅ **方便使用** - 在 VSCode 里直接输入命令就能生成项目

---

## 📊 现状分析（关键发现）

### 第一个关键点：workflow 是同步的

**用人话说**：
```python
# src/main.py 中的代码
app = build_graph()
final_state = app.invoke(...)  # 这行会一直等，直到所有工作完成
```

这个 `invoke()` 会"卡住"，等整个流程跑完才继续。

**为什么重要**？
- 如果直接在服务器里调用，会导致服务器"假死"
- 解决办法：开一个后台线程专门跑这个，主线程继续干别的

#### 2. **Agents 已经在保存中间结果**

```python
# agents/architecture_agent.py (第86行)
def save_arch_json(self, repo_dir: str, steps: int, arch_data: dict):
    arch_json_path = f"{repo_dir}/tmp_files/architecture_{steps}.json"
    with open(arch_json_path, "w", encoding="utf-8") as f:
    第二个关键点：agents 会自动保存进度

**用人话说**：
你的代码在运行时会自动保存文件：
```
tmp_files/
  ├── architecture_1.json  ← 架构设计第1次迭代
  ├── architecture_2.json  ← 架构设计第2次迭代
  ├── skeleton_1.json      ← 骨架代码第1次迭代
  └── generated_code_1.jsonl ← 最终生成的代码
```

**为什么重要**？
- ✅ 不需要改动原有代码，它已经在保存进度了
- ✅ 第三个关键点：路径写死了

**用人话说**：
代码里有些路径是写死的：
```python
# 这样写在别的电脑上会找不到文件
code_judge_agent.TEST_BASE_DIR = "/home/zhaoqianhui/workspace/..."
base_dir = '../datasets'
```

**怎么解决**？
- 用环境变量（.env 文件）配置路径
- 每个人的电脑路径不一样，配置一下就能用

### 第四个关键点：Continue 提供的能力

**用人话说**：
Continue 能帮我们做这些事：
- 📖 **读文件**：`ide.readFile(路径)` - 读取 PRD.md
- ✍️ **写文件**：`ide.writeFile(路径, 内容)` - 把生成的代码写到工作区
- 📁 **获取工作区**：`ide.getWorkspaceDirs()` - 知道当前项目在哪
- 💬 **聊天界面**：显示进度、错误信息🏗️ 修订后的架构设计

### 三层结构

```
第1层：用户界面（Continue 聊天窗口）
┌─────────────────────────────────────────────────┐
│  用户在 VSCode 的 Continue Chat 里输入：       │
│  /projectgen repo=bplustree                     │
│                                                 │
│  Continue 做这些事：                            │
│  1. 读取 datasets/bplustree/PRD.md             │
│  2. 调用后台服务器启动生成                      │
│  3. 每隔3秒问一次："生成完了吗？到哪一步了？"   │
│  4. 生成完后，把代码写到工作区                  │
└─────────────────────────────────────────────────┘
         │ (通过 HTTP 通信)
         ↓
第2层：后台服务器（新增的 FastAPI 服务器）
┌─────────────────────────────────────────────────┐
│  这是一个轻量级的"中转站"：                     │
│                                                 │
│  - 接收 Continue 的请求                        │
│  - 启动一个后台线程运行 workflow               │
│  - 定期查看 tmp_files/ 目录了解进度            │
│  - 把进度和结果返回给 Continue                 │
└─────────────────────────────────────────────────┘
         │ (直接调用 Python 函数)
         ↓
第3层：ProjectGen 核心（你的 src/ 代码，不动！）
┌─────────────────────────────────────────────────┐
│  这就是你原来的代码：                           │
│                                                 │
│  workflow.py → agents/ → 生成文件              │
│                                                 │
│  完全不需要知道"外面有个 Continue"              │
└─────────────────────────────────────────────────┘
```

### 工作文件结构（重要！看这里）

```
codegen-on-continue/                ← 【注意】正确的项目名
│
├── src/                          ← 【不动】你原来的代码
│   ├── workflow.py              
│   ├── main.py                   
│   ├── agents/                   
│   ├── memory_manager/           
│   └── ...                       
│
├── projectgen-server/            ← 【新增】中转服务器（很简单）
│   ├── main.py                   ← 约180行的代码（含完整错误处理）
│   ├── progress_monitor.py       ← 约80行的代码（更健壮的解析）
│   ├── requirements.txt          ← 4个依赖包
│   └── .env                      ← 配置文件（设置路径）
│
├── continue/                     ← 【小改】只加一个命令
│   └── core/commands/slash/built-in-legacy/
│       ├── index.ts              ← 改2行（导入+注册命令）
│       └── projectgen.ts         ← 新增（约350行）
│
├── datasets/                     ← 【不动】你的数据集
│   ├── CodeProjectEval/
│   │   └── bplustree/
│   │       ├── config.json       ← 配置文件（指定PRD等路径）
│   │       └── docs/
│   │           └── PRD.md        ← 【注意】PRD在docs子目录下
│   └── DevBench/
│
└── outputs/                      ← 【自动创建】生成的代码保存在这里
```

### 关于 config.json 的重要说明

每个项目的 `config.json` 指定了各个文件的相对路径：

```json
{
    "PRD": "docs/PRD.md",              // PRD文件路径
    "UML": ["docs/UML.md", "docs/UML_pyreverse.md"],  // UML文件
    "architecture_design": "docs/architecture_design.md",
    "language": "python",
    ...
}
```

**关键**：代码需要先读取 `config.json`，然后拼接路径读取实际文件！

### 新增文件说明

**projectgen-server/main.py**  
作用：一个轻量级的中转站
- 提供3个接口：启动任务、查询进度、获取文件
- 开后台线程调用你的 workflow
- 不涉及复杂逻辑

**projectgen-server/progress_monitor.py**  
作用：查看进度的工具函数
- 检查 tmp_files/ 目录里有哪些文件
- 判断当前在哪个阶段（architecture/skeleton/code）

**continue/.../projectgen.ts**  
作用：Continue 的命令实现
- 读取用户输入
- 调用服务器接口
- 显示进度
- 写入生成的文件
  "project_id": "abc-123-def",  // 任务编号
  "status": "pending"
}
```

**第4步：服务器启动后台任务**
```python
# 服务器在后台开个线程跑这个
def run_workflow_sync(project_id, initial_state):
    from workflow import build_graph
    graph = build_graph()
    final_state = graph.invoke(initial_state)  # 这行会跑很久
    # 跑完了，标记为完成
```

**第5步：Continue 轮询进度**
```
每隔3秒，Continue 问服务器：
GET http://localhost:5000/api/projects/abc-123-def/status

服务器回答：
{
  "status": "running",
  "current_stage": "architecture",  // 当前在做架构设计
  "iteration": 2,                    // 第2次迭代
  "progress": 25                     // 完成了25%
}

Continue 在聊天窗口显示：
🏗️ Architecture Design
  - Iteration 1
  - Iteration 2
[█████░░░░░░░░░░░░░░░] 25%
```

**第6步：获取生成的文件**
```
任务完成后，Continue 问：
GET http://localhost:5000/api/projects/abc-123-def/files

服务器回答：
{
  "files": [
    {"path": "bplustree.py", "content": "class BPlusTree:..."},
    {"path": "node.py", "content": "class Node:..."},
    ...
  ]
}
```

**第7步：写入工作区**
```
Continue 把这些文件写到：
CodeProjectEval_outputs/bplustree/bplustree.py
CodeProjectEval_outputs/bplustree/node.py
...

完成！
│
├── datasets/                               # 保持不变
│   ├── CodeProjectEval/
│   └── DevBench/
│
└── doc/
    └── FINAL_DESIGN_PROPOSAL_REVISED.md    # 本文档
```

---

## 🔧 核心代码（看懂这些就够了）

### 1. 后台服务器 - `projectgen-server/main.py`

这个文件做什么？充当"中转站"，接收 Continue 的请求，调用你的 workflow。

**核心代码**（带注释）：

```python
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
import sys, os, json, uuid

# 把 src/ 加到路径里，这样就能 import workflow 了
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=3)  # 最多同时跑3个任务

# 任务记录（简单起见用字典，生产环境可以用数据库）
tasks = {}

@app.post("/api/projects/generate")
async def generate_project(request):
    """启动生成任务 - Continue 会调用这个"""
    project_id = str(uuid.uuid4())  # 生成任务编号
    
    # 准备输入数据（跟你的 main.py 里一样）
    initial_state = {
        "user_input": request.requirement,
        "uml_class": request.uml_class,
        "arch_design": request.arch_design,
        "repo_name": request.repo_name,
        "code_file_DAG": [...],
        "repo_dir": f"outputs/{request.repo_name}",
        "dataset": request.dataset
    }
    
    # 记录任务信息
    tasks[project_id] = {
        "status": "pending",      # 状态：等待中
        "current_stage": "architecture",
        "iteration": 0,
        "progress": 0,
        "repo_dir": f"outputs/{request.repo_name}"
    }
    
    # 开个后台线程去跑（不会卡住服务器）
    executor.submit(run_workflow_sync, project_id, initial_state)
    
    return {"project_id": project_id}


def run_workflow_sync(project_id, initial_state):
    """这个函数在后台线程里跑，就是调用你的 workflow"""
    from workflow import build_graph
    
    try:
        tasks[project_id]["status"] = "running"  # 标记为运行中
        
        # 就这一行！调用你的代码
        graph = build_graph()
        final_state = graph.invoke(initial_state, config={"recursion_limit": 50})
        
        # 跑完了，标记完成
        tasks[project_id]["status"] = "completed"
        tasks[project_id]["progress"] = 100
        
    except Exception as e:
        tasks[project_id]["status"] = "failed"
        tasks[project_id]["error"] = str(e)


@app.get("/api/projects/{project_id}/status")
async def get_status(project_id):
    """查询进度 - Continue 会每隔3秒调用一次"""
    task = tasks[project_id]
    
    # 如果正在运行，去 tmp_files/ 看看跑到哪了
    if task["status"] == "running":
        stage, iteration = detect_current_stage(task["repo_dir"])
        task["current_stage"] = stage
        task["iteration"] = iteration
        task["progress"] = calculate_progress(stage, iteration)
    
    return task


@app.get("/api/projects/{project_id}/files")
async def get_files(project_id):
    """获取生成的文件 - 任务完成后 Continue 调用这个"""
    repo_dir = tasks[project_id]["repo_dir"]
    
    # 读取最新的 generated_code_*.jsonl 文件
    code_file = f"{repo_dir}/tmp_files/generated_code_final.jsonl"
    
    files = []
    with open(code_file) as f:
        for line in f:
            item = json.loads(line)
            files.append({
                "path": item["path"],
                "content": item["code"]
            })
    
    return {"files": files}


# 启动服务器
if __name__ == "__main__":
    import uvicorn
    print("🚀 服务器启动在 http://localhost:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

**关键点**：
- 只有 `graph.invoke(...)` 这一行是调用你的代码
- 其他都是"包装"工作：接收请求、返回结果
- 需要导入 `calculate_progress` 函数

### 完整的服务器代码 `projectgen-server/main.py`

```python
"""
ProjectGen Server - 轻量级 API 服务器
用于接收 Continue 的请求，调用 src/workflow.py 生成代码
"""

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

# 加载环境变量
load_dotenv()

# 添加 src 到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from progress_monitor import detect_current_stage, calculate_progress

app = FastAPI(title="ProjectGen Server", version="1.0.0")

# CORS - 允许 Continue 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
DATASET_BASE_DIR = os.getenv(
    "PROJECTGEN_DATASET_DIR", 
    os.path.join(PROJECT_ROOT, "datasets")
)
OUTPUT_BASE_DIR = os.getenv(
    "PROJECTGEN_OUTPUT_DIR",
    os.path.join(PROJECT_ROOT, "outputs")
)

# 线程池
executor = ThreadPoolExecutor(max_workers=3)

# 任务存储 (生产环境应使用 Redis/DB)
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
    """健康检查"""
    return {
        "status": "healthy",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "total_tasks": len(tasks),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/projects/generate")
async def generate_project(request: GenerateRequest):
    """启动项目生成任务"""
    project_id = str(uuid.uuid4())
    
    # 验证数据集和 repo 存在
    repo_source_dir = os.path.join(DATASET_BASE_DIR, request.dataset, request.repo_name)
    if not os.path.exists(repo_source_dir):
        raise HTTPException(404, f"Repository not found: {repo_source_dir}")
    
    # 创建输出目录
    repo_output_dir = os.path.join(OUTPUT_BASE_DIR, request.model, request.repo_name)
    os.makedirs(repo_output_dir, exist_ok=True)
    os.makedirs(os.path.join(repo_output_dir, "tmp_files"), exist_ok=True)
    
    # 读取配置文件
    config_path = os.path.join(repo_source_dir, "config.json")
    if not os.path.exists(config_path):
        raise HTTPException(404, f"config.json not found in {repo_source_dir}")
    
    with open(config_path) as f:
        repo_config = json.load(f)
    
    # 准备初始状态
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
    
    # 创建任务记录
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
    
    # 提交到线程池
    executor.submit(run_workflow_sync, project_id, initial_state)
    
    return {
        "project_id": project_id,
        "status": "pending",
        "message": f"Generation task created for {request.repo_name}"
    }


def run_workflow_sync(project_id: str, initial_state: dict):
    """在后台线程中同步执行 workflow"""
    from workflow import build_graph
    
    try:
        # 更新状态为运行中
        tasks[project_id]["status"] = "running"
        tasks[project_id]["message"] = "Workflow started..."
        
        # 构建和执行 graph
        graph = build_graph()
        final_state = graph.invoke(initial_state, config={"recursion_limit": 50})
        
        # 更新为完成状态
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
    """获取项目状态（含实时进度检测）"""
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    
    # 如果任务正在运行，检测实际进度
    if task["status"] == "running":
        repo_dir = task["repo_dir"]
        stage, iteration = detect_current_stage(repo_dir)
        
        task["current_stage"] = stage
        task["iteration"] = iteration
        
        # 估算进度
        stage_progress = {
            "architecture": 20,
            "skeleton": 50,
            "code": 80
        }
        base_progress = stage_progress.get(stage, 0)
        task["progress"] = min(95, base_progress + iteration * 5)
    
    return ProjectStatus(**task)


@app.get("/api/projects/{project_id}/files")
async def get_generated_files(project_id: str):
    """获取生成的文件列表和内容"""
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    
    if task["status"] != "completed":
        raise HTTPException(400, "Project not completed yet")
    
    repo_dir = task["repo_dir"]
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    files = []
    
    # 查找最新的 code_*.jsonl 文件
    code_files = [f for f in os.listdir(tmp_dir) if f.startswith("generated_code_")]
    if not code_files:
        return {"files": []}
    
    # 获取最新的文件
    latest_code_file = sorted(code_files)[-1]
    code_jsonl_path = os.path.join(tmp_dir, latest_code_file)
    
    # 读取生成的代码
    with open(code_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            files.append({
                "path": item["path"],
                "content": item["code"]
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
    print(f"🚀 ProjectGen Server starting...")
    print(f"📁 Dataset directory: {DATASET_BASE_DIR}")
    print(f"📁 Output directory: {OUTPUT_BASE_DIR}")
    print(f"🌐 Server running on http://0.0.0.0:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
```

### 2. 进度监控器 - `projectgen-server/progress_monitor.py`

这个文件做什么？通过查看 tmp_files/ 目录里的文件，判断当前进度。

**核心逻辑**（更健壮的版本）：

```python
import os
import re
from typing import Tuple, List

def detect_current_stage(repo_dir: str) -> Tuple[str, int]:
    """
    查看 tmp_files/ 里有哪些文件，判断当前执行到哪个阶段
    
    返回: (阶段名, 最大迭代次数)
    阶段: "architecture" | "skeleton" | "code"
    """
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    # 目录不存在 = 还没开始
    if not os.path.exists(tmp_dir):
        return "architecture", 0
    
    files = os.listdir(tmp_dir)
    
    # 提取文件中的数字（支持多种命名格式）
    def extract_step_numbers(files: List[str], prefix: str) -> List[int]:
        """从文件名中提取步骤数字"""
        numbers = []
        for f in files:
            if f.startswith(prefix):
                # 尝试匹配各种格式: xxx_1.json, xxx_step1.json, xxx1.json
                match = re.search(r'(\d+)', f.replace(prefix, ''))
                if match:
                    numbers.append(int(match.group(1)))
        return numbers
    
    # 检查代码生成阶段（最后阶段）
    code_numbers = extract_step_numbers(files, "generated_code")
    if code_numbers:
        return "code", max(code_numbers)
    
    # 检查骨架生成阶段
    skeleton_numbers = extract_step_numbers(files, "skeleton")
    if skeleton_numbers:
        return "skeleton", max(skeleton_numbers)
    
    # 检查架构设计阶段
    arch_numbers = extract_step_numbers(files, "architecture")
    if arch_numbers:
        return "architecture", max(arch_numbers)
    
    # 都没有 = 刚开始
    return "architecture", 0


def calculate_progress(stage: str, iteration: int) -> int:
    """
    根据阶段和迭代次数估算进度百分比
    
    进度分配:
    - architecture: 0-30%
    - skeleton: 30-60%  
    - code: 60-100%
    """
    stage_config = {
        "architecture": {"base": 0, "max": 30, "weight": 10},
        "skeleton": {"base": 30, "max": 60, "weight": 10},
        "code": {"base": 60, "max": 100, "weight": 8}
    }
    
    if stage not in stage_config:
        return 0
    
    config = stage_config[stage]
    progress = config["base"] + min(iteration * config["weight"], config["max"] - config["base"])
    
    return min(95, progress)  # 最多95%，完成时才100%


class ProgressMonitor:
    """进度监控器类，提供更丰富的进度信息"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
        self.tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    def get_status(self) -> dict:
        """获取完整的进度状态"""
        stage, iteration = detect_current_stage(self.repo_dir)
        progress = calculate_progress(stage, iteration)
        
        return {
            "current_stage": stage,
            "iteration": iteration,
            "progress": progress,
            "files": self._list_generated_files()
        }
    
    def _list_generated_files(self) -> List[str]:
        """列出已生成的文件"""
        if not os.path.exists(self.tmp_dir):
            return []
        return sorted(os.listdir(self.tmp_dir))
```

**理解要点**：
- 不需要改动 agents/ 的代码
- 只是"旁观者"，看看文件系统了解进度
- 支持多种文件命名格式
- 提供进度百分比估算

---

### 3. Continue 命令 - `continue/core/commands/slash/built-in-legacy/projectgen.ts`

这个文件做什么？Continue 聊天窗口的命令实现，负责：
1. 读取 PRD.md
2. 调用服务器
3. 显示进度
4. 写入生成的文件

**核心流程**（分段解释）：

#### 第1部分：读取配置

```typescript
// 用户输入：/projectgen repo=bplustree dataset=CodeProjectEval
const config = parseInput(input, params);

// 获取工作区路径
const workspaceDirs = await ide.getWorkspaceDirs();
const workspaceDir = workspaceDirs[0];  // 比如：/Users/lv.sany/.../codegen-on-continue

// 【重要】先读取 config.json 获取文件路径
const configPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/config.json`;
const configContent = await ide.readFile(configPath);
const repoConfig = JSON.parse(configContent);

// 然后根据 config.json 中指定的路径读取 PRD.md
const prdPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/${repoConfig.PRD}`;
const requirement = await ide.readFile(prdPath);
// 注意：repoConfig.PRD 的值是 "docs/PRD.md"，所以实际路径是 .../bplustree/docs/PRD.md
```

#### 第2部分：启动任务

```typescript
// 【重要】fetch 是从 ContinueSDK 参数中解构获取的，不是全局的 fetch
// SlashCommand.run 的签名是: run: (sdk: ContinueSDK) => AsyncGenerator<string>
// sdk 包含: { ide, llm, input, params, fetch, abortController, ... }

const response = await fetch(`http://localhost:5000/api/projects/generate`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    repo_name: config.repo_name,
    requirement: requirement,
    dataset: config.dataset,
    model: config.model,
    uml_class: umlClass,      // 从 config.json 读取的 UML
    arch_design: archDesign   // 从 config.json 读取的架构设计
  })
});

const { project_id } = await response.json();
// 得到任务编号，比如：abc-123-def
```

#### 第3部分：轮询进度

```typescript
// 【重要】需要检查 abortController.signal 来支持用户取消
while (!isComplete) {
  // 检查是否被用户取消
  if (abortController.signal.aborted) {
    yield "\n⚠️ Generation cancelled by user\n";
    break;
  }
  
  await sleep(3000);  // 等3秒
  
  // 问服务器：跑到哪了？
  const status = await fetch(`http://localhost:5000/api/projects/${project_id}/status`);
  const statusData = await status.json();
  
  // 在聊天窗口显示进度
  if (statusData.current_stage === "architecture") {
    yield "🏗️ Architecture Design - Iteration " + statusData.iteration + "\n";
  }
  
  // 显示进度条
  yield `[████████░░░░░░░░░░░░] ${statusData.progress}%\n`;
  
  // 如果完成了，跳出循环
  if (statusData.status === "completed") {
    isComplete = true;
  } else if (statusData.status === "failed") {
    yield `\n❌ Error: ${statusData.error}\n`;
    return;  // 提前退出
  }
}
```

#### 第4部分：获取并写入文件

```typescript
// 获取生成的文件
const filesData = await fetch(`http://localhost:5000/api/projects/${project_id}/files`);
const files = filesData.files;  // [{path: "bplustree.py", content: "..."}, ...]

// 写入到工作区
for (const file of files) {
  const fullPath = `${workspaceDir}/CodeProjectEval_outputs/${config.repo_name}/${file.path}`;
  await ide.writeFile(fullPath, file.content);
  yield `✓ ${file.path}\n`;
}

yield "🎉 完成！\n";
```

**理解要点**：
- 这个文件就是"界面逻辑"
- 不涉及代码生成的核心算法
- 总共约350行，大部分是显示和格式化
- **fetch 从 SDK 参数解构获取，不是全局变量**
- **需要检查 abortController 支持用户取消**

### 完整的 projectgen.ts 代码

```typescript
/**
 * ProjectGen Slash Command for Continue
 * 
 * 用法: /projectgen repo=<repo_name> [dataset=<dataset>] [model=<model>]
 * 例如: /projectgen repo=bplustree dataset=CodeProjectEval model=gpt-4o
 */

import { SlashCommand } from "../../../index.js";

// 类型定义
interface GeneratedFile {
  path: string;
  content: string;
}

interface RepoConfig {
  PRD: string;
  UML?: string[];
  architecture_design?: string;
  language?: string;
  code_file_DAG?: string[];
}

interface ProjectStatus {
  project_id: string;
  status: "pending" | "running" | "completed" | "failed";
  current_stage: string;
  iteration: number;
  progress: number;
  message?: string;
  error?: string;
  result?: {
    arch_steps?: number;
    skeleton_steps?: number;
    code_steps?: number;
  };
}

// 服务器地址（可配置）
const SERVER_URL = "http://localhost:5000";

const ProjectGenSlashCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a complete project using multi-agent workflow",
  run: async function* ({ ide, input, params, fetch, abortController }) {
    // 【重要】fetch 是从 SDK 参数中解构获取的，不是全局 fetch
    
    try {
      // 1. 解析用户输入
      const config = parseInput(input, params);
      
      yield "🚀 **ProjectGen - Multi-Agent Project Generation**\n\n";
      
      if (!config.repo_name) {
        yield "❌ Error: Please specify repository name\n";
        yield "Usage: `/projectgen repo=<name> [dataset=<dataset>] [model=<model>]`\n";
        yield "Example: `/projectgen repo=bplustree dataset=CodeProjectEval`\n";
        return;
      }
      
      yield "📋 **Configuration:**\n";
      yield `- Repository: \`${config.repo_name}\`\n`;
      yield `- Dataset: \`${config.dataset}\`\n`;
      yield `- Model: \`${config.model}\`\n\n`;
      
      // 2. 获取工作区目录
      const workspaceDirs = await ide.getWorkspaceDirs();
      if (!workspaceDirs || workspaceDirs.length === 0) {
        yield "❌ Error: No workspace folder open\n";
        return;
      }
      const workspaceDir = workspaceDirs[0];
      
      // 3. 【修正】先读取 config.json 获取文件路径
      yield "📖 Reading project configuration...\n";
      const repoDir = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}`;
      const configPath = `${repoDir}/config.json`;
      
      let repoConfig: RepoConfig;
      try {
        const configContent = await ide.readFile(configPath);
        repoConfig = JSON.parse(configContent);
      } catch (e) {
        yield `❌ Error: Cannot read config.json at ${configPath}\n`;
        yield `Please ensure the file exists.\n`;
        return;
      }
      
      // 4. 【修正】根据 config.json 读取 PRD
      yield "📖 Reading PRD...\n";
      const prdPath = `${repoDir}/${repoConfig.PRD}`;  // 例如: .../bplustree/docs/PRD.md
      let requirement: string;
      try {
        requirement = await ide.readFile(prdPath);
        yield `✅ PRD loaded (${requirement.length} chars)\n\n`;
      } catch (e) {
        yield `❌ Error: Cannot read PRD file at ${prdPath}\n`;
        yield `(config.json specifies PRD as "${repoConfig.PRD}")\n`;
        return;
      }
      
      // 5. 读取其他配置文件（UML、架构设计等）
      let umlClass = "";
      let archDesign = "";
      
      try {
        if (repoConfig.architecture_design) {
          const archPath = `${repoDir}/${repoConfig.architecture_design}`;
          archDesign = await ide.readFile(archPath);
          yield `✅ Architecture design loaded\n`;
        }
        
        // 读取 UML（优先使用 pyreverse 版本）
        if (repoConfig.UML && repoConfig.UML.length > 0) {
          for (const umlFile of repoConfig.UML) {
            if (umlFile.includes("pyreverse")) {
              const umlPath = `${repoDir}/${umlFile}`;
              umlClass = await ide.readFile(umlPath);
              yield `✅ UML loaded (${umlFile})\n`;
              break;
            }
          }
          // 如果没有 pyreverse 版本，使用第一个
          if (!umlClass && repoConfig.UML.length > 0) {
            const umlPath = `${repoDir}/${repoConfig.UML[0]}`;
            umlClass = await ide.readFile(umlPath);
            yield `✅ UML loaded (${repoConfig.UML[0]})\n`;
          }
        }
      } catch (e) {
        // 这些文件是可选的，读取失败不影响继续
        yield `⚠️ Some optional files could not be loaded\n`;
      }
      
      yield "\n";
      
      // 6. 检查服务器连接
      yield "🔌 Connecting to ProjectGen server...\n";
      try {
        const healthCheck = await fetch(`${SERVER_URL}/api/health`);
        if (!healthCheck.ok) {
          yield "❌ Error: Server returned error status\n";
          return;
        }
        const healthData = await healthCheck.json();
        yield `✅ Server connected (${healthData.active_tasks} active tasks)\n\n`;
      } catch (e) {
        yield "❌ Error: Cannot connect to ProjectGen server\n";
        yield "Please start the server:\n";
        yield "```bash\n";
        yield "cd projectgen-server && python main.py\n";
        yield "```\n";
        return;
      }
      
      // 7. 启动生成任务
      yield "📤 Starting generation task...\n";
      const startResponse = await fetch(`${SERVER_URL}/api/projects/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset: config.dataset,
          repo_name: config.repo_name,
          requirement,
          uml_class: umlClass,
          uml_sequence: "",  // DevBench 才需要
          arch_design: archDesign,
          model: config.model,
          code_file_DAG: repoConfig.code_file_DAG || [],
        }),
      });
      
      if (!startResponse.ok) {
        const errorText = await startResponse.text();
        yield `❌ Error: ${errorText}\n`;
        return;
      }
      
      const { project_id } = await startResponse.json();
      yield `🆔 Project ID: \`${project_id}\`\n\n`;
      
      // 8. 显示工作流图
      yield "📊 **Workflow:**\n\n";
      yield "```\n";
      yield "┌──────────────┐     ┌──────────────┐     ┌──────────────┐\n";
      yield "│Architecture │ ──> │  Skeleton    │ ──> │    Code      │\n";
      yield "│   Design     │     │ Generation   │     │ Filling      │\n";
      yield "└──────────────┘     └──────────────┘     └──────────────┘\n";
      yield "     ↓ Judge             ↓ Judge             ↓ Judge\n";
      yield "   (Iterate)            (Iterate)           (Iterate)\n";
      yield "```\n\n";
      
      // 9. 轮询状态
      yield "⏳ **Progress:**\n\n";
      let lastStage = "";
      let lastIteration = 0;
      let isComplete = false;
      
      while (!isComplete) {
        // 【重要】检查用户是否取消
        if (abortController.signal.aborted) {
          yield "\n⚠️ Generation cancelled by user\n";
          // TODO: 可以调用服务器的取消接口
          return;
        }
        
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        const statusResponse = await fetch(`${SERVER_URL}/api/projects/${project_id}/status`);
        if (!statusResponse.ok) {
          yield `❌ Error checking status\n`;
          return;
        }
        
        const status: ProjectStatus = await statusResponse.json();
        
        // 检测阶段变化
        if (status.current_stage !== lastStage) {
          const emoji = getStageEmoji(status.current_stage);
          const stageName = formatStageName(status.current_stage);
          yield `\n${emoji} **${stageName}**\n`;
          lastStage = status.current_stage;
          lastIteration = 0;
        }
        
        // 检测迭代变化
        if (status.iteration > lastIteration) {
          yield `  - Iteration ${status.iteration}\n`;
          lastIteration = status.iteration;
        }
        
        // 显示进度条
        const bar = generateProgressBar(status.progress);
        yield `${bar} ${status.progress}%\n`;
        
        if (status.status === "completed") {
          yield "\n🎉 **Generation Completed!**\n\n";
          
          // 10. 获取生成的文件
          yield "📥 Retrieving generated files...\n";
          const filesResponse = await fetch(`${SERVER_URL}/api/projects/${project_id}/files`);
          if (!filesResponse.ok) {
            yield "❌ Error retrieving files\n";
            return;
          }
          
          const filesData = await filesResponse.json();
          const files: GeneratedFile[] = filesData.files;
          
          if (!files || files.length === 0) {
            yield "⚠️ No files generated\n";
            return;
          }
          
          yield `✅ Retrieved ${files.length} files\n\n`;
          
          // 11. 写入文件到工作区
          yield "📝 Writing files to workspace...\n";
          const outputDir = `${config.dataset}_outputs/${config.repo_name}`;
          
          for (const file of files) {
            const fullPath = `${workspaceDir}/${outputDir}/${file.path}`;
            try {
              await ide.writeFile(fullPath, file.content);
              yield `  ✓ ${file.path}\n`;
            } catch (e) {
              yield `  ✗ ${file.path} (error: ${e})\n`;
            }
          }
          
          yield `\n📁 Output directory: \`${outputDir}\`\n\n`;
          
          // 12. 显示统计
          if (status.result) {
            yield "📊 **Statistics:**\n";
            yield `- Architecture iterations: ${status.result.arch_steps || 0}\n`;
            yield `- Skeleton iterations: ${status.result.skeleton_steps || 0}\n`;
            yield `- Code iterations: ${status.result.code_steps || 0}\n`;
            yield `- Total files: ${files.length}\n`;
          }
          
          isComplete = true;
        } else if (status.status === "failed") {
          yield `\n❌ **Generation Failed**\n`;
          yield `Error: ${status.error || "Unknown error"}\n`;
          isComplete = true;
        }
      }
      
    } catch (error: any) {
      yield `\n❌ **Unexpected Error**: ${error.message}\n`;
      console.error("ProjectGen error:", error);
    }
  }
};

// 辅助函数
function parseInput(input: string, params: any): { dataset: string; repo_name: string; model: string } {
  const config = {
    dataset: params?.dataset || "CodeProjectEval",
    repo_name: "",
    model: params?.model || "gpt-4o"
  };
  
  // 从输入字符串解析参数
  const repoMatch = input.match(/repo=(\S+)/);
  if (repoMatch) config.repo_name = repoMatch[1];
  
  const datasetMatch = input.match(/dataset=(\S+)/);
  if (datasetMatch) config.dataset = datasetMatch[1];
  
  const modelMatch = input.match(/model=(\S+)/);
  if (modelMatch) config.model = modelMatch[1];
  
  return config;
}

function getStageEmoji(stage: string): string {
  const map: Record<string, string> = {
    "architecture": "🏗️",
    "skeleton": "🦴",
    "code": "💻"
  };
  return map[stage] || "⚙️";
}

function formatStageName(stage: string): string {
  const map: Record<string, string> = {
    "architecture": "Architecture Design",
    "skeleton": "Skeleton Generation",
    "code": "Code Implementation"
  };
  return map[stage] || stage;
}

function generateProgressBar(progress: number, width: number = 20): string {
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  return `[${"█".repeat(filled)}${"░".repeat(empty)}]`;
}

export default ProjectGenSlashCommand;
```

---

### 4. 注册命令 - 修改 `continue/core/commands/slash/built-in-legacy/index.ts`

这个文件做什么？告诉 Continue："嘿，我们新增了一个 /projectgen 命令"

**需要改2行**：

```typescript
// ① 在文件顶部添加导入（在其他 import 语句附近）
import ProjectGenSlashCommand from "./projectgen.js";

// ② 在数组里添加我们的命令
const LegacyBuiltInSlashCommands: SlashCommand[] = [
  DraftIssueCommand,
  ShareSlashCommand,
  GenerateTerminalCommand,
  HttpSlashCommand,
  CommitMessageCommand,
  ReviewMessageCommand,
  OnboardSlashCommand,
  ProjectGenSlashCommand,  // ← 加这一行！
];
```

**⚠️ 注意事项**：
1. 导入路径必须加 `.js` 后缀（TypeScript 编译要求）
2. 确保 `projectgen.ts` 文件已创建在同一目录下

---

## 🚀 实施步骤（手把手教你）

### 第一步：创建后台服务器（30分钟）

#### 1.1 创建目录

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue
mkdir projectgen-server
cd projectgen-server
```

#### 1.2 创建 requirements.txt

```bash
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
python-dotenv==1.0.0
EOF
```

#### 1.3 安装依赖

```bash
pip install -r requirements.txt
```

#### 1.4 创建 .env 配置文件

```bash
cat > .env << 'EOF'
PROJECTGEN_DATASET_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue/datasets
PROJECTGEN_OUTPUT_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue/outputs
PORT=5000
EOF
```

说明：这两个路径根据你的实际路径修改。

#### 1.5 创建 main.py

**完整代码见附录A**（约150行）

要点：
- 导入 workflow
- 提供3个 API 接口
- 使用线程池执行 workflow

#### 1.6 创建 progress_monitor.py

**完整代码见附录B**（约50行）

要点：
- 检查 tmp_files/ 目录
- 判断当前阶段

#### 1.7 测试服务器

```bash
python main.py
```

看到这个说明成功了：
```
🚀 ProjectGen Server starting...
📁 Dataset directory: /Users/.../datasets
📁 Output directory: /Users/.../outputs
🌐 Server running on http://0.0.0.0:5000
```

---

### 第二步：修改 Continue 代码（1小时）

#### 2.1 找到 Continue 目录

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue/continue
```

#### 2.2 创建 projectgen.ts

```bash
cd core/commands/slash/built-in-legacy
touch projectgen.ts
```

**完整代码见附录C**（约300行）

要点：
- 解析用户输入
- 读取 PRD.md
- 调用服务器接口
- 显示进度
- 写入文件

#### 2.3 修改 index.ts

找到文件：`continue/core/commands/slash/built-in-legacy/index.ts`

在**第1行**后面加一行：
```typescript
import ProjectGenSlashCommand from "./projectgen.js";
```

在数组里加一个元素（找到 `LegacyBuiltInSlashCommands` 数组）：
```typescript
const LegacyBuiltInSlashCommands: SlashCommand[] = [
  DraftIssueCommand,
  ShareSlashCommand,
  GenerateTerminalCommand,
  HttpSlashCommand,
  CommitMessageCommand,
  ReviewMessageCommand,
  OnboardSlashCommand,
  ProjectGenSlashCommand,  // ← 加这一行
];
```

#### 2.4 编译 Continue

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue/continue/extensions/vscode
npm install  # 第一次需要
npm run compile
```

编译成功会显示：
```
Compilation complete. Watching for file changes.
```

**⚠️ 编译可能遇到的问题**：

1. **TypeScript 类型错误**：确保 `projectgen.ts` 中的类型定义正确
2. **模块找不到**：检查导入路径是否正确（需要 `.js` 后缀）
3. **Node.js 版本**：确保使用 18.0+ 版本

---

### 第三步：测试完整流程（30分钟）

#### 3.1 启动服务器

在一个终端：
```bash
cd projectgen-server
python main.py
```

#### 3.2 启动 VSCode 调试

1. 在 VSCode 中打开 `continue` 文件夹
2. 按 `F5` 键（或者点击"Run" → "Start Debugging"）
3. 会弹出一个新的 VSCode 窗口（这就是调试窗口）

#### 3.3 使用命令

在新的 VSCode 窗口中：

1. 打开你的项目文件夹（codegen-on-continue）
2. 按 `Cmd+L`（Mac）或 `Ctrl+L`（Windows）打开 Continue Chat
3. 输入命令：
   ```
   /projectgen repo=bplustree dataset=CodeProjectEval
   ```
4. 观察输出！

---

### 第四步：预期效果

你会看到这样的输出：

```
🚀 ProjectGen - Multi-Agent Project Generation

📋 Configuration:
- Repository: `bplustree`
- Dataset: `CodeProjectEval`
- Model: `gpt-4o`

📖 Reading PRD...
✅ PRD loaded (1234 chars)

🔌 Connecting to ProjectGen server...
✅ Server connected

📤 Starting generation task...
🆔 Project ID: `abc-123-def`

📊 Workflow:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│Architecture │ ──> │  Skeleton    │ ──> │    Code      │
│   Design     │     │ Generation   │     │ Filling      │
└──────────────┘     └──────────────┘     └──────────────┘

⏳ Progress:

🏗️ Architecture Design
  - Iteration 1
  - Iteration 2
[████████░░░░░░░░░░░░] 20%

🦴 Skeleton Generation
  - Iteration 1
[████████████████░░░░] 50%

💻 Code Implementation
  - Iteration 1
  - Iteration 2
[████████████████████] 100%

🎉 Generation Completed!

📥 Retrieving generated files...
✅ Retrieved 8 files

📝 Writing files to workspace...
  ✓ bplustree.py
  ✓ node.py
  ✓ test_bplustree.py
  ...

📁 Output directory: `CodeProjectEval_outputs/bplustree`

📊 Statistics:
- Architecture iterations: 2
- Skeleton iterations: 1
- Code iterations: 2
- Total files: 8
```

---

## 📊 总结：你需要写多少代码？

| 文件 | 行数 | 难度 | 说明 |
|------|------|------|------|
| `projectgen-server/main.py` | ~180行 | ⭐⭐ | 主要是API接口定义 |
| `projectgen-server/progress_monitor.py` | ~80行 | ⭐ | 文件查找和解析 |
| `continue/.../projectgen.ts` | ~350行 | ⭐⭐⭐ | TypeScript，需要理解异步 |
| `continue/.../index.ts` | 修改2行 | ⭐ | 导入+注册命令 |
| **总计** | **~610行新代码** | - | src/ 完全不动！ |

---

## 🎯 关键理念再强调

### 你的 src/ 代码：

```
不需要改！
不需要改！！
不需要改！！！
```

### 新增的代码只做3件事：

1. **服务器（main.py）**：接收请求 → 调用 workflow → 返回结果
2. **进度监控（progress_monitor.py）**：看文件 → 判断进度
3. **Continue 命令（projectgen.ts）**：读config.json → 读PRD → 调服务器 → 显示进度 → 写文件

### 这就是"套壳"：

- **壳**：Continue 的聊天界面 + 文件操作能力
- **核心**：你的 workflow.py、agents/ 等代码
- **中转站**：一个轻量级的 FastAPI 服务器

---

## 📋 常见问题补充

### Q1: 为什么 PRD 路径要通过 config.json 读取？

因为不同项目的 PRD 文件位置不同。例如：
- `bplustree` 的 PRD 在 `docs/PRD.md`
- 其他项目可能在不同位置

### Q2: ContinueSDK 中的 fetch 和全局 fetch 有什么区别？

Continue 提供的 `fetch` 可能经过了代理处理，能更好地处理跨域和身份验证。始终使用从参数解构的 `fetch`。

### Q3: 为什么需要 AbortController？

用户可能在生成过程中取消操作。检查 `abortController.signal.aborted` 可以优雅地处理取消，而不是让任务一直运行。

### Q4: generated_code 文件的格式是什么？

是 JSONL 格式（每行一个 JSON），结构如下：
```json
{"path": "bplustree.py", "content": "class BPlusTree:..."}
{"path": "node.py", "content": "class Node:..."}
```

### Q5: workflow.py 中的硬编码路径怎么处理？

当前 `workflow.py` 中有些硬编码路径（如 `TEST_BASE_DIR`）。建议：
1. 服务器启动时设置环境变量
2. 或者修改 `workflow.py` 读取环境变量（这需要改 src/，但改动很小）

### Q6: 如何支持 DevBench 数据集？

DevBench 需要额外的 `uml_sequence` 参数，当前代码已支持：
1. 在 `projectgen.ts` 中判断 dataset 类型
2. 如果是 DevBench，额外读取 `UML_sequence` 文件

---

## 📝 修订历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 5.0 | 2026-01-21 | 初始版本 |
| 6.0 | 2026-01-22 | 修正路径、TypeScript类型、config.json读取逻辑、AbortController支持 |

---

## 🔗 参考资源

- [Continue 文档](https://docs.continue.dev/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
