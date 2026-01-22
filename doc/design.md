# ProjectGen × Continue "套壳"集成方案

**版本**: 5.0 (简化版，易于理解)  
**日期**: 2026年1月21日  
**核心理念**: Continue 只提供聊天界面，ProjectGen 核心代码(src/)完全不动

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

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Continue VSCode Extension                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  SlashCommand: /projectgen                            │  │
│  │  1. 解析参数 (repo, dataset)                         │  │
│  │  2. 读取 PRD.md (使用 IDE.readFile)                  │  │
│  │  3. POST /api/projects/generate                      │  │
│  │  4. 轮询 GET /api/projects/{id}/status               │  │
│  │  5. 读取生成的文件 (从 repo_dir/tmp_files/)         │  │
│  │  6. 写入到工作区 (使用 IDE.writeFile)                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    ↕ HTTP
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Server (projectgen-server/)                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                            │  │
│  │  - POST /api/projects/generate                        │  │
│  │  - GET  /api/projects/{id}/status                     │  │
│  │  -整体架构（通俗版）

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
new-projectgen/
│
├── src/                          ← 【不动】你原来的代码
│   ├── workflow.py              
│   ├── main.py                   
│   ├── agents/                   
│   ├── memory_manager/           
│   └── ...                       
│
├── projectgen-server/            ← 【新增】中转服务器（很简单）
│   ├── main.py                   ← 150行左右的代码
│   ├── progress_monitor.py       ← 50行左右的代码
│   ├── requirements.txt          ← 4个依赖包
│   └── .env                      ← 配置文件（设置路径）
│
├── continue/                     ← 【小改】只加一个命令
│   └── core/commands/slash/built-in-legacy/
│       ├── index.ts              ← 改1行（注册命令）
│       └── projectgen.ts         ← 新增（300行左右）
│
├── datasets/                     ← 【不动】你的数据集
│   ├── CodeProjectEval/
│   └── DevBench/
│
└── outputs/                      ← 【自动创建】生成的代码保存在这里
```

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
- 总共不到150行代码

```python
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

# 添加 src 到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from progress_monitor import ProgressMonitor, detect_current_stage

app = FastAPI(title="ProjectGen Server", version="1.0.0")

# CORS
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

**核心逻辑**（很简单）：

```python
import os

def detect_current_stage(repo_dir):
    """看看 tmp_files/ 里有哪些文件，判断跑到哪了"""
    tmp_dir = f"{repo_dir}/tmp_files"
    
    # 目录不存在 = 还没开始
    if not os.path.exists(tmp_dir):
        return "architecture", 0
    
    files = os.listdir(tmp_dir)
    
    # 如果有 generated_code_*.jsonl = 在跑代码生成
    code_files = [f for f in files if f.startswith("generated_code_")]
    if code_files:
        # 找最大的数字，比如 generated_code_3.jsonl → 第3次迭代
        max_step = max([int(f.split("_")[-1].replace(".jsonl", "")) 
                       for f in code_files])
        return "code", max_step
    
    # 如果有 skeleton_*.json = 在跑骨架生成
    skeleton_files = [f for f in files if f.startswith("skeleton_")]
    if skeleton_files:
        max_step = max([int(f.split("_")[-1].replace(".json", "")) 
                       for f in skeleton_files])
        return "skeleton", max_step
    
    # 如果有 architecture_*.json = 在跑架构设计
    arch_files = [f for f in files if f.startswith("architecture_")]
    if arch_files:
        max_step = max([int(f.split("_")[-1].replace(".json", "")) 
                       for f in arch_files])
        return "architecture", max_step
    
    return "architecture", 0
```

**理解要点**：
- 不需要改动 agents/ 的代码
- 只是"旁观者"，看看文件系统了解进度
- 总共50行代码

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
const workspaceDir = workspaceDirs[0];  // 比如：/Users/lv.sany/.../new-projectgen

// 读取 PRD.md
const prdPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/PRD.md`;
const requirement = await ide.readFile(prdPath);
```

#### 第2部分：启动任务

```typescript
// 发送请求到服务器
const response = await fetch(`http://localhost:5000/api/projects/generate`, {
  method: "POST",
  body: JSON.stringify({
    repo_name: config.repo_name,
    requirement: requirement,
    dataset: config.dataset,
    model: config.model
  })
});

const { project_id } = await response.json();
// 得到任务编号，比如：abc-123-def
```

#### 第3部分：轮询进度

```typescript
// 每隔3秒问一次
while (!isComplete) {
  await sleep(3000);  // 等3秒
  
  // 问服务器：跑到哪了？
  const status = await fetch(`http://localhost:5000/api/projects/${project_id}/status`);
  
  // 在聊天窗口显示进度
  if (status.current_stage === "architecture") {
    yield "🏗️ Architecture Design - Iteration " + status.iteration + "\n";
  }
  
  // 显示进度条
  yield `[████████░░░░░░░░░░░░] ${status.progress}%\n`;
  
  // 如果完成了，跳出循环
  if (status.status === "completed") {
    isComplete = true;
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
- 总共300行左右，大部分是显示和格式化
      // 2. 获取工作区目录
      const workspaceDirs = await ide.getWorkspaceDirs();
      if (!workspaceDirs || workspaceDirs.length === 0) {
        yield "❌ Error: No workspace folder open\n";
        return;
      }
      const workspaceDir = workspaceDirs[0];
      
      // 3. 读取 PRD.md
      yield "📖 Reading PRD...\n";
      const prdPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/PRD.md`;
      let requirement: string;
      try {
        requirement = await ide.readFile(prdPath);
        yield `✅ PRD loaded (${requirement.length} chars)\n\n`;
      } catch (e) {
        yield `❌ Error: Cannot read PRD file at ${prdPath}\n`;
        yield `Please ensure the file exists.\n`;
        return;
      }
      
      // 4. 读取其他配置文件（如果存在）
      let umlClass = "";
      let archDesign = "";
      try {
        const configPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/config.json`;
        const configContent = await ide.readFile(configPath);
        const repoConfig = JSON.parse(configContent);
        
        if (repoConfig.architecture_design) {
          const archPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/${repoConfig.architecture_design}`;
          archDesign = await ide.readFile(archPath);
        }
        
        if (repoConfig.UML && repoConfig.UML.length > 0) {
          const umlPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/${repoConfig.UML[0]}`;
          umlClass = await ide.readFile(umlPath);
        }
      } catch (e) {
        // 配置文件可选，失败不影响继续
      }
      
      // 5. 检查服务器连接
      yield "🔌 Connecting to ProjectGen server...\n";
      try {
        const healthCheck = await fetch(`${serverUrl}/api/health`);
        if (!healthCheck.ok) {
          yield "❌ Error: Server returned error status\n";
          return;
        }
        yield "✅ Server connected\n\n";
      } catch (e) {
        yield "❌ Error: Cannot connect to ProjectGen server\n";
        yield `Please start the server: \`cd projectgen-server && python main.py\`\n`;
        return;
      }
      
      // 6. 启动生成任务
      yield "📤 Starting generation task...\n";
      const startResponse = await fetch(`${serverUrl}/api/projects/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset: config.dataset,
          repo_name: config.repo_name,
          requirement,
          uml_class: umlClass,
          arch_design: archDesign,
          model: config.model,
        }),
      });
      
      if (!startResponse.ok) {
        const errorText = await startResponse.text();
        yield `❌ Error: ${errorText}\n`;
        return;
      }
      
      const { project_id } = await startResponse.json();
      yield `🆔 Project ID: \`${project_id}\`\n\n`;
      
      // 7. 显示工作流图
      yield "📊 **Workflow:**\n\n";
      yield "```\n";
      yield "┌──────────────┐     ┌──────────────┐     ┌──────────────┐\n";
      yield "│Architecture │ ──> │  Skeleton    │ ──> │    Code      │\n";
      yield "│   Design     │     │ Generation   │     │ Filling      │\n";
      yield "└──────────────┘     └──────────────┘     └──────────────┘\n";
      yield "     ↓ Judge             ↓ Judge             ↓ Judge\n";
      yield "   (Iterate)            (Iterate)           (Iterate)\n";
      yield "```\n\n";
      
      // 8. 轮询状态
      yield "⏳ **Progress:**\n\n";
      let lastStage = "";
      let lastIteration = 0;
      let isComplete = false;
      
      while (!isComplete) {
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        const statusResponse = await fetch(`${serverUrl}/api/projects/${project_id}/status`);
        if (!statusResponse.ok) {
          yield `❌ Error checking status\n`;
          return;
        }
        
        const status = await statusResponse.json();
        
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
        yield `\r${bar} ${status.progress}%`;
        
        if (status.status === "completed") {
          yield "\n\n🎉 **Generation Completed!**\n\n";
          
          // 9. 获取生成的文件
          yield "📥 Retrieving generated files...\n";
          const filesResponse = await fetch(`${serverUrl}/api/projects/${project_id}/files`);
          if (!filesResponse.ok) {
            yield "❌ Error retrieving files\n";
            return;
          }
          
          const filesData = await filesResponse.json();
          const files: GeneratedFile[] = filesData.files;
          
          if (!files || files.length === 0) {
            yield "⚠️  No files generated\n";
            return;
          }
          
          yield `✅ Retrieved ${files.length} files\n\n`;
          
          // 10. 写入文件到工作区
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
          
          // 11. 显示统计
          if (status.result) {
            yield "📊 **Statistics:**\n";
            yield `- Architecture iterations: ${status.result.arch_steps || 0}\n`;
            yield `- Skeleton iterations: ${status.result.skeleton_steps || 0}\n`;
            yield `- Code iterations: ${status.result.code_steps || 0}\n`;
            yield `- Total files: ${files.length}\n`;
          }
          
          isComplete = true;
        } else if (status.status === "failed") {
          yield `\n\n❌ **Generation Failed**\n`;
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

function parseInput(input: string, params: any): any {
  const config: any = {
    dataset: params?.dataset || "CodeProjectEval",
    repo_name: "",
    model: params?.model || "gpt-4o"
  };
  
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

**只需改1行**：

```typescript
// 在文件顶部添加导入
import ProjectGenSlashCommand from "./projectgen.js";

// 在数组里添加我们的命令
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

---

## 🚀 实施步骤（手把手教你）

### 第一步：创建后台服务器（30分钟）

#### 1.1 创建目录

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen
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
PROJECTGEN_DATASET_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/datasets
PROJECTGEN_OUTPUT_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/outputs
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
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/continue
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
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/continue/extensions/vscode
npm install  # 第一次需要
npm run compile
```

编译成功会显示：
```
Compilation complete. Watching for file changes.
```

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

1. 打开你的项目文件夹（new-projectgen）
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
| `projectgen-server/main.py` | ~150行 | ⭐⭐ | 主要是API接口定义 |
| `projectgen-server/progress_monitor.py` | ~50行 | ⭐ | 很简单的文件查找 |
| `continue/.../projectgen.ts` | ~300行 | ⭐⭐⭐ | TypeScript，需要理解异步 |
| `continue/.../index.ts` | 修改2行 | ⭐ | 只是注册命令 |
| **总计** | **~500行新代码** | - | src/ 完全不动！ |

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
3. **Continue 命令（projectgen.ts）**：读PRD → 调服务器 → 显示进度 → 写文件

### 这就是"套壳"：

- **壳**：Continue 的聊天界面 + 文件操作能力
- **核心**：你的 workflow.py、agents/ 等代码
- **中转站**：一个轻量级的 FastAPI 服务器

---

## 附录
