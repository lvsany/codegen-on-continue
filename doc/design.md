# ProjectGen × Continue 集成方案 - 修订版

**版本**: 4.0 (基于实际代码修正)  
**日期**: 2026年1月21日  
**状态**: 待审核

---

## 📊 实际代码分析

### 核心发现

#### 1. **workflow.py 是同步执行的**

```python
# src/workflow.py
def build_graph():
    builder = StateGraph(dict)
    # ... 添加节点
    return builder.compile()

# src/main.py
app = build_graph()
final_state = app.invoke(initial_state, config={"recursion_limit": 50})
# ⚠️ invoke() 是同步阻塞的，会等待整个工作流完成
```

**影响**：
- ❌ 无法直接使用 `asyncio.create_task()` 实现异步
- ✅ 需要使用线程池来避免阻塞 FastAPI
- ✅ 可以通过检查文件系统来监控进度

#### 2. **Agents 已经在保存中间结果**

```python
# agents/architecture_agent.py (第86行)
def save_arch_json(self, repo_dir: str, steps: int, arch_data: dict):
    arch_json_path = f"{repo_dir}/tmp_files/architecture_{steps}.json"
    with open(arch_json_path, "w", encoding="utf-8") as f:
        json.dump(arch_data, f, ensure_ascii=False, indent=2)

# agents/skeleton_agent.py (第148行)
skeleton_json_path = f"{repo_dir}/tmp_files/skeleton_{steps}.json"

# agents/code_agent.py (第290行)
code_jsonl_path = f"{repo_dir}/tmp_files/generated_code_{steps}.jsonl"
```

**关键洞察**：
- ✅ 不需要额外的回调机制
- ✅ 可以通过轮询 `tmp_files/` 目录来监控进度
- ✅ 最终结果已经保存在文件中，可以直接读取

#### 3. **记忆管理器的实际结构**

```python
# memory_manager/arch_memory.py
class FullInputMemory(BaseChatMessageHistory):
    def __init__(self, max_prompt_history: int = 2):
        self.full_history: List[Dict] = []
        self.messages: List[BaseMessage] = []
    
    def save_context(self, inputs: Dict, outputs: Dict):
        # 保存在内存中，没有持久化
```

**影响**：
- ⚠️ 记忆只在进程生命周期内有效
- ⚠️ FastAPI 服务器重启会丢失记忆
- ✅ 可以通过 `full_history` 导出记忆内容

#### 4. **硬编码的路径问题**

```python
# workflow.py (第31行)
code_judge_agent.TEST_BASE_DIR = "/home/zhaoqianhui/workspace/new-projectgen/datasets/"

# main.py (第22行)
base_dir = '../datasets'
```

**影响**：
- ⚠️ 在不同环境下会失败
- ✅ 需要通过环境变量配置

#### 5. **Continue IDE API 的实际接口**

```typescript
// continue/core/index.d.ts
interface IDE {
  getWorkspaceDirs(): Promise<string[]>;  // 获取工作区目录
  readFile(fileUri: string): Promise<string>;  // 读取文件 (URI格式)
  writeFile(path: string, contents: string): Promise<void>;  // 写入文件
}
```

---

## 🏗️ 修订后的架构设计

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
│  │  - GET  /api/projects/{id}/files                      │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ThreadPoolExecutor                                    │  │
│  │  - 在后台线程中执行 workflow                          │  │
│  │  - 通过检查文件系统监控进度                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    ↕ 直接调用
┌─────────────────────────────────────────────────────────────┐
│  ProjectGen Core (src/) - 完全不修改                        │
│  - workflow.py: build_graph() + app.invoke()                │
│  - agents/: 6个智能体 (自动保存到 tmp_files/)              │
│  - memory_manager/: 记忆管理                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
new-projectgen/
├── src/                                    # 完全不修改
│   ├── workflow.py
│   ├── main.py
│   └── agents/
│
├── projectgen-server/                      # 新增 FastAPI 服务器
│   ├── main.py                             # 服务器主文件
│   ├── progress_monitor.py                 # 进度监控器
│   ├── models.py                           # Pydantic 模型
│   ├── requirements.txt
│   └── .env.example                        # 环境变量示例
│
├── continue/                               # 最小修改
│   └── core/commands/slash/built-in-legacy/
│       ├── index.ts                        # 修改：注册命令
│       └── projectgen.ts                   # 新增：命令实现
│
├── datasets/                               # 保持不变
│   ├── CodeProjectEval/
│   └── DevBench/
│
└── doc/
    └── FINAL_DESIGN_PROPOSAL_REVISED.md    # 本文档
```

---

## 🔧 核心组件实现

### 1. FastAPI 服务器 - `projectgen-server/main.py`

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

```python
import os
from typing import Tuple


def detect_current_stage(repo_dir: str) -> Tuple[str, int]:
    """
    通过检查已生成的文件来推断当前阶段和迭代次数
    
    Returns:
        (stage, iteration): 阶段名称和迭代次数
    """
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    if not os.path.exists(tmp_dir):
        return "architecture", 0
    
    try:
        files = os.listdir(tmp_dir)
    except Exception:
        return "architecture", 0
    
    # 检查 code_*.jsonl 文件（最高优先级）
    code_files = [f for f in files if f.startswith("generated_code_") and f.endswith(".jsonl")]
    if code_files:
        max_step = max([int(f.replace("generated_code_", "").replace(".jsonl", "")) 
                       for f in code_files])
        return "code", max_step
    
    # 检查 skeleton_*.json 文件
    skeleton_files = [f for f in files if f.startswith("skeleton_") and f.endswith(".json")]
    if skeleton_files:
        max_step = max([int(f.replace("skeleton_", "").replace(".json", "")) 
                       for f in skeleton_files])
        return "skeleton", max_step
    
    # 检查 architecture_*.json 文件
    arch_files = [f for f in files if f.startswith("architecture_") and f.endswith(".json")]
    if arch_files:
        max_step = max([int(f.replace("architecture_", "").replace(".json", "")) 
                       for f in arch_files])
        return "architecture", max_step
    
    return "architecture", 0


class ProgressMonitor:
    """进度监控器（可选，用于更复杂的进度追踪）"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
    
    def get_stage_info(self) -> dict:
        """获取详细的阶段信息"""
        stage, iteration = detect_current_stage(self.repo_dir)
        
        return {
            "stage": stage,
            "iteration": iteration,
            "stage_display": self._get_stage_display(stage),
            "emoji": self._get_stage_emoji(stage)
        }
    
    def _get_stage_display(self, stage: str) -> str:
        mapping = {
            "architecture": "Architecture Design",
            "skeleton": "Skeleton Generation",
            "code": "Code Implementation"
        }
        return mapping.get(stage, stage)
    
    def _get_stage_emoji(self, stage: str) -> str:
        mapping = {
            "architecture": "🏗️",
            "skeleton": "🦴",
            "code": "💻"
        }
        return mapping.get(stage, "⚙️")
```

### 3. Continue SlashCommand - `continue/core/commands/slash/built-in-legacy/projectgen.ts`

```typescript
import { SlashCommand } from "../../../index.js";

interface GeneratedFile {
  path: string;
  content: string;
}

const ProjectGenSlashCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a project using ProjectGen multi-agent framework",
  
  run: async function* ({ ide, input, params, fetch }) {
    const serverUrl = params?.serverUrl || "http://localhost:5000";
    
    try {
      yield "🚀 **ProjectGen** - Multi-Agent Project Generation\n\n";
      
      // 1. 解析参数
      const config = parseInput(input, params);
      if (!config.repo_name) {
        yield "❌ Error: Missing required parameter 'repo'\n";
        yield "Usage: `/projectgen repo=<name> [dataset=CodeProjectEval]`\n";
        return;
      }
      
      yield `📋 Configuration:\n`;
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

### 4. 注册 SlashCommand - 修改 `continue/core/commands/slash/built-in-legacy/index.ts`

```typescript
// 在文件顶部添加导入
import ProjectGenSlashCommand from "./projectgen.js";

// 在 LegacyBuiltInSlashCommands 数组中添加
const LegacyBuiltInSlashCommands: SlashCommand[] = [
  DraftIssueCommand,
  ShareSlashCommand,
  GenerateTerminalCommand,
  HttpSlashCommand,
  CommitMessageCommand,
  ReviewMessageCommand,
  OnboardSlashCommand,
  ProjectGenSlashCommand,  // ← 添加这一行
];
```

---

## 🚀 实施步骤

### Phase 1: 创建 FastAPI 服务器（1-2天）

**步骤**：
1. 创建 `projectgen-server/` 目录
2. 实现 `main.py`、`progress_monitor.py`、`models.py`
3. 创建 `requirements.txt`:
   ```
   fastapi==0.104.1
   uvicorn==0.24.0
   pydantic==2.4.2
   python-dotenv==1.0.0
   ```
4. 创建 `.env.example`:
   ```
   PROJECTGEN_DATASET_DIR=/path/to/datasets
   PROJECTGEN_OUTPUT_DIR=/path/to/outputs
   PORT=5000
   ```
5. 测试服务器：
   ```bash
   cd projectgen-server
   pip install -r requirements.txt
   python main.py
   ```

**测试**：
```bash
# 健康检查
curl http://localhost:5000/api/health

# 启动生成任务
curl -X POST http://localhost:5000/api/projects/generate \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "CodeProjectEval",
    "repo_name": "bplustree",
    "requirement": "Test requirement",
    "model": "gpt-4o"
  }'

# 查询状态
curl http://localhost:5000/api/projects/{project_id}/status
```

### Phase 2: 实现 Continue SlashCommand（2-3天）

**步骤**：
1. 在 `continue/core/commands/slash/built-in-legacy/` 创建 `projectgen.ts`
2. 修改 `index.ts` 注册命令
3. 编译 Continue:
   ```bash
   cd continue/extensions/vscode
   npm install
   npm run compile
   ```
4. 在 VSCode 中按 F5 启动调试

**测试**：
1. 打开新的 VSCode 窗口（Extension Development Host）
2. 打开 Continue Chat 面板（Cmd/Ctrl + L）
3. 输入：`/projectgen repo=bplustree dataset=CodeProjectEval`
4. 观察输出

### Phase 3: 端到端测试（1-2天）

**测试场景**：
1. ✅ 正常流程：architecture → skeleton → code
2. ✅ 迭代场景：多次迭代优化
3. ✅ 错误处理：服务器未启动、repo 不存在
4. ✅ 文件写入：生成的代码正确应用到工作区
5. ✅ 多任务：并发执行多个生成任务

---

## 📊 预期效果

### Continue Chat 中的显示

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
🆔 Project ID: `abc-123-def-456`

📊 Workflow:

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│Architecture │ ──> │  Skeleton    │ ──> │    Code      │
│   Design     │     │ Generation   │     │ Filling      │
└──────────────┘     └──────────────┘     └──────────────┘
     ↓ Judge             ↓ Judge             ↓ Judge
   (Iterate)            (Iterate)           (Iterate)

⏳ Progress:

🏗️ Architecture Design
  - Iteration 1
  - Iteration 2
[████████████████████] 20%

🦴 Skeleton Generation
  - Iteration 1
[████████████████████████████] 50%

💻 Code Implementation
  - Iteration 1
  - Iteration 2
  - Iteration 3
[████████████████████████████████████████] 100%

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
- Code iterations: 3
- Total files: 8
```

---

## ⚠️ 已解决的问题

### ✅ 问题1: workflow 同步阻塞
**解决方案**: 使用 `ThreadPoolExecutor` 在后台线程执行

### ✅ 问题2: 无法监听进度
**解决方案**: 通过检查 `tmp_files/` 目录中的文件来推断进度

### ✅ 问题3: 文件访问路径
**解决方案**: 使用环境变量配置基础路径

### ✅ 问题4: 记忆管理
**解决方案**: 记忆保存在内存中，FastAPI 进程内可访问（可选功能）

### ✅ 问题5: Continue IDE API
**解决方案**: 使用 `getWorkspaceDirs()` 获取工作区，`readFile/writeFile` 处理文件

---

## 🎯 下一步行动

**立即开始**：
1. 确认设计方案是否符合需求
2. 创建 `projectgen-server/` 目录结构
3. 实现基础的 FastAPI 服务器
4. 进行端到端测试

**需要确认的问题**：
1. ✅ 输出目录是否使用 `outputs/` 而不是 `{dataset}_outputs/`？
2. ✅ 是否需要支持取消正在运行的任务？
3. ✅ 是否需要持久化任务历史（使用 SQLite/Redis）？
4. ✅ 是否需要实现记忆查看功能？

准备好开始实施了吗？
