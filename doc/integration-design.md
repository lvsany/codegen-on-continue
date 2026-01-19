# ProjectGen × Continue VSCode 插件 - HTTP 集成方案设计文档

**版本**: 1.0  
**日期**: 2026年1月14日  
**状态**: 设计阶段

---

## 📋 目录

1. [整体架构](#整体架构)
2. [技术选型](#技术选型)
3. [项目结构](#项目结构)
4. [核心模块设计](#核心模块设计)
5. [通信协议](#通信协议)
6. [部署方案](#部署方案)
7. [实施路线图](#实施路线图)
8. [风险与挑战](#风险与挑战)

---

## 🎯 设计目标

将 ProjectGen 多智能体项目生成框架集成到 Continue VSCode 插件中，实现：

- ✅ 在 Continue Chat 界面中通过斜杠命令触发项目生成
- ✅ 实时显示多阶段生成进度（架构设计、骨架生成、代码填充）
- ✅ 将生成的代码自动应用到 VSCode 工作区
- ✅ 提供记忆上下文查看功能
- ✅ 支持本地和远程部署

---

## 🏗️ 整体架构

### 架构图

```
┌────────────────────────────────────────────────────────────┐
│  VSCode Extension (TypeScript)                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Continue Framework                                   │ │
│  │  ├─ GUI Panel (React)                                │ │
│  │  ├─ SlashCommand: /projectgen                        │ │
│  │  ├─ ContextProvider: @projectgen-memory              │ │
│  │  └─ WebSocket Client (实时通信)                      │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                    ↕ (HTTP/WebSocket)
┌────────────────────────────────────────────────────────────┐
│  ProjectGen Server (Python FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  HTTP Endpoints                                       │ │
│  │  ├─ POST /api/projects/generate                      │ │
│  │  ├─ GET  /api/projects/{id}/status                   │ │
│  │  ├─ GET  /api/projects/{id}/memory                   │ │
│  │  └─ WS   /api/ws/{id}                                │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  ProjectGen Core (LangGraph Workflow)                │ │
│  │  ├─ ArchitectureAgent → ArchJudgeAgent              │ │
│  │  ├─ SkeletonAgent → SkeletonJudgeAgent              │ │
│  │  └─ CodeAgent → CodeJudgeAgent                       │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### 分层设计

| 层级 | 技术栈 | 职责 |
|------|--------|------|
| **UI层** | Continue GUI (React) | 用户交互、进度展示、代码预览 |
| **插件层** | TypeScript + VSCode API | 命令注册、文件管理、编辑器集成 |
| **通信层** | HTTP + WebSocket | 前后端通信、实时推送 |
| **服务层** | FastAPI | API 路由、请求处理、状态管理 |
| **引擎层** | LangGraph + LangChain | 多智能体生成、迭代、记忆管理 |

---

## 🛠️ 技术选型

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| TypeScript | ^5.0 | 类型安全的开发 |
| VSCode API | ^1.70.0 | 编辑器集成 |
| Continue SDK | Latest | SlashCommand、ContextProvider |
| WebSocket API | Native | 实时通信 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 核心语言 |
| FastAPI | ^0.104 | Web 框架 |
| Uvicorn | ^0.24 | ASGI 服务器 |
| LangGraph | Latest | 工作流编排 |
| LangChain | Latest | LLM 调用 |
| Pydantic | ^2.0 | 数据验证 |

### 为什么选择 HTTP + WebSocket？

**HTTP**：
- ✅ 简单可靠的请求-响应模式
- ✅ 适合一次性操作（启动任务、查询状态）
- ✅ 易于调试和测试
- ✅ 支持缓存和负载均衡

**WebSocket**：
- ✅ 全双工实时通信
- ✅ 低延迟的进度推送
- ✅ 减少轮询开销
- ✅ 适合长时间运行任务

---

## 📁 项目结构

```
new-projectgen/
├── README.md
├── doc/                                # 设计文档
│   └── integration-design.md
│
├── packages/
│   ├── projectgen-core/                # Python 核心（重构）
│   │   ├── pyproject.toml
│   │   ├── setup.py
│   │   ├── requirements.txt
│   │   └── src/
│   │       └── projectgen/
│   │           ├── __init__.py
│   │           ├── agents/
│   │           │   ├── __init__.py
│   │           │   ├── architecture_agent.py
│   │           │   ├── arch_judge_agent.py
│   │           │   ├── skeleton_agent.py
│   │           │   ├── skeleton_judge_agent.py
│   │           │   ├── code_agent.py
│   │           │   └── code_judge_agent.py
│   │           ├── memory_manager/
│   │           │   ├── __init__.py
│   │           │   ├── arch_memory.py
│   │           │   ├── skeleton_memory.py
│   │           │   └── code_memory.py
│   │           ├── workflow.py
│   │           ├── utils.py
│   │           ├── prompts.py
│   │           ├── logger.py
│   │           └── generation_schema.py
│   │
│   ├── projectgen-server/              # FastAPI HTTP 网关（新建）
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   └── src/
│   │       ├── main.py                 # FastAPI 入口
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── routes.py           # HTTP 路由
│   │       │   └── websocket.py        # WebSocket 处理
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── request.py          # 请求模型
│   │       │   └── response.py         # 响应模型
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   └── generator.py        # 调用 projectgen-core
│   │       └── utils/
│   │           ├── __init__.py
│   │           └── stream.py           # 流式处理工具
│   │
│   └── projectgen-vscode-plugin/       # VSCode 插件扩展（新建）
│       ├── package.json
│       ├── tsconfig.json
│       ├── README.md
│       └── src/
│           ├── index.ts                # 导出入口
│           ├── projectgen-command.ts   # SlashCommand 实现
│           ├── projectgen-context.ts   # ContextProvider 实现
│           ├── api-client.ts           # HTTP/WS 客户端
│           ├── types.ts                # 类型定义
│           └── utils/
│               ├── config.ts           # 配置管理
│               ├── logger.ts           # 日志
│               └── file-handler.ts     # 文件操作
│
├── continue/                           # Continue 框架（保留）
│   └── extensions/vscode/
│       └── src/
│           └── extension.ts            # 注册 ProjectGen 插件
│
└── datasets/                           # 数据集（保留）
    ├── CodeProjectEval/
    └── DevBench/
```

---

## 🔧 核心模块设计

### 1. ProjectGen Server (FastAPI)

#### 1.1 主入口 - `packages/projectgen-server/src/main.py`

```python
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import uuid
from typing import Dict, Optional
from datetime import datetime
import logging

from models.request import GenerateRequest, GenerateResponse
from models.response import TaskStatus, ProjectResult
from services.generator import ProjectGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProjectGen Server",
    version="1.0.0",
    description="Multi-agent project generation service"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局任务存储（生产环境应使用 Redis）
tasks: Dict[str, TaskStatus] = {}
generator = ProjectGenerator()

@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "ProjectGen Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "total_tasks": len(tasks),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/projects/generate", response_model=GenerateResponse)
async def generate_project(request: GenerateRequest):
    """
    启动项目生成任务
    
    Args:
        request: 包含 dataset, repo_name, requirement 等配置
        
    Returns:
        GenerateResponse: 包含 project_id 和状态
    """
    try:
        # 生成唯一 ID
        project_id = str(uuid.uuid4())
        
        # 初始化任务状态
        tasks[project_id] = {
            "id": project_id,
            "status": "pending",
            "progress": 0,
            "current_stage": "initialization",
            "stages": {
                "architecture": {"status": "pending", "progress": 0},
                "skeleton": {"status": "pending", "progress": 0},
                "code": {"status": "pending", "progress": 0}
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": request.dict(),
            "logs": []
        }
        
        logger.info(f"Created task {project_id} for repo {request.repo_name}")
        
        # 异步启动生成任务
        asyncio.create_task(run_generation_workflow(project_id, request))
        
        return GenerateResponse(
            project_id=project_id,
            status="started",
            message="Project generation started successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to start generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """获取任务状态"""
    if project_id not in tasks:
        raise HTTPException(status_code=404, detail="Project not found")
    return tasks[project_id]

@app.get("/api/projects/{project_id}/memory/{stage}")
async def get_project_memory(project_id: str, stage: str):
    """
    获取特定阶段的记忆内容
    
    Args:
        project_id: 项目 ID
        stage: 阶段名称 (architecture/skeleton/code)
    """
    if project_id not in tasks:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 这里应该从实际的内存管理器中读取
    # 简化版本直接返回示例
    return {
        "project_id": project_id,
        "stage": stage,
        "memory": f"Memory content for {stage} stage"
    }

@app.websocket("/api/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket 实时推送任务进度
    
    客户端连接后会持续接收任务状态更新，直到任务完成或失败
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for project {project_id}")
    
    try:
        last_update = None
        
        while True:
            if project_id not in tasks:
                await websocket.send_json({
                    "error": "Project not found",
                    "project_id": project_id
                })
                break
            
            task_data = tasks[project_id]
            
            # 只在状态变化时发送
            if task_data != last_update:
                await websocket.send_json(task_data)
                last_update = task_data.copy()
            
            # 任务完成则关闭连接
            if task_data["status"] in ["completed", "failed"]:
                logger.info(f"Task {project_id} finished with status: {task_data['status']}")
                break
            
            await asyncio.sleep(0.5)  # 500ms 轮询一次
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.delete("/api/projects/{project_id}")
async def cancel_project(project_id: str):
    """取消正在运行的任务"""
    if project_id not in tasks:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = tasks[project_id]
    if task["status"] == "running":
        task["status"] = "cancelled"
        task["updated_at"] = datetime.now().isoformat()
        return {"message": "Task cancelled successfully"}
    
    return {"message": f"Task is already {task['status']}"}

async def run_generation_workflow(project_id: str, request: GenerateRequest):
    """
    运行 ProjectGen 核心工作流
    
    这个函数会调用现有的 LangGraph 工作流，并更新任务状态
    """
    try:
        # 更新为运行状态
        tasks[project_id]["status"] = "running"
        tasks[project_id]["updated_at"] = datetime.now().isoformat()
        
        # 运行生成器
        result = await generator.generate(
            project_id=project_id,
            config=request,
            progress_callback=lambda stage, progress, message: update_task_progress(
                project_id, stage, progress, message
            )
        )
        
        # 完成
        tasks[project_id]["status"] = "completed"
        tasks[project_id]["progress"] = 100
        tasks[project_id]["result"] = result
        tasks[project_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Task {project_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {project_id} failed: {e}")
        tasks[project_id]["status"] = "failed"
        tasks[project_id]["error"] = str(e)
        tasks[project_id]["updated_at"] = datetime.now().isoformat()

def update_task_progress(project_id: str, stage: str, progress: int, message: str = ""):
    """更新任务进度"""
    if project_id in tasks:
        tasks[project_id]["current_stage"] = stage
        tasks[project_id]["progress"] = progress
        tasks[project_id]["updated_at"] = datetime.now().isoformat()
        
        if stage in tasks[project_id]["stages"]:
            tasks[project_id]["stages"][stage]["status"] = "running"
            tasks[project_id]["stages"][stage]["progress"] = progress
        
        if message:
            tasks[project_id]["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "message": message
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
```

#### 1.2 生成器服务 - `packages/projectgen-server/src/services/generator.py`

```python
import asyncio
import sys
import os
from typing import Callable, Dict, Any

# 添加 projectgen-core 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../projectgen-core/src"))

from projectgen.workflow import build_graph
from models.request import GenerateRequest

class ProjectGenerator:
    """ProjectGen 核心生成器包装类"""
    
    def __init__(self):
        self.graph = None
    
    async def generate(
        self,
        project_id: str,
        config: GenerateRequest,
        progress_callback: Callable[[str, int, str], None]
    ) -> Dict[str, Any]:
        """
        执行项目生成
        
        Args:
            project_id: 项目 ID
            config: 生成配置
            progress_callback: 进度回调函数 (stage, progress, message)
            
        Returns:
            生成结果字典
        """
        try:
            # 构建工作流
            if not self.graph:
                self.graph = build_graph()
            
            progress_callback("initialization", 5, "Initializing workflow...")
            
            # 准备初始状态
            initial_state = {
                "user_input": config.requirement,
                "uml_class": config.uml_class or "",
                "uml_sequence": "",
                "arch_design": "",
                "repo_name": config.repo_name,
                "code_file_DAG": config.code_file_dag or [],
                "dataset": config.dataset
            }
            
            progress_callback("architecture", 10, "Starting architecture design...")
            
            # 在事件循环中运行（LangGraph 可能是同步的）
            final_state = await asyncio.to_thread(
                self._run_sync_workflow,
                initial_state,
                progress_callback
            )
            
            progress_callback("completed", 100, "Generation completed!")
            
            # 返回结果
            return {
                "arch_design": final_state.get("arch_design"),
                "skeleton_design": final_state.get("skeleton_design"),
                "generated_files": final_state.get("generated_files", []),
                "stats": {
                    "arch_iterations": final_state.get("arch_steps", 0),
                    "skeleton_iterations": final_state.get("skeleton_steps", 0),
                    "code_iterations": final_state.get("code_steps", 0)
                }
            }
            
        except Exception as e:
            progress_callback("failed", 0, f"Error: {str(e)}")
            raise
    
    def _run_sync_workflow(
        self,
        initial_state: Dict[str, Any],
        progress_callback: Callable[[str, int, str], None]
    ) -> Dict[str, Any]:
        """同步运行工作流"""
        
        # 这里可以添加钩子来获取中间状态
        # 目前简化处理
        final_state = self.graph.invoke(initial_state)
        
        return final_state
```

#### 1.3 请求模型 - `packages/projectgen-server/src/models/request.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class GenerateRequest(BaseModel):
    """项目生成请求模型"""
    
    dataset: str = Field(
        default="CodeProjectEval",
        description="数据集名称"
    )
    repo_name: str = Field(
        ...,
        description="仓库名称"
    )
    requirement: str = Field(
        ...,
        description="项目需求描述（PRD 内容）"
    )
    uml_class: Optional[str] = Field(
        None,
        description="UML 类图（可选）"
    )
    code_file_dag: Optional[List[str]] = Field(
        None,
        description="文件依赖 DAG（可选）"
    )
    model: str = Field(
        default="gpt-4o",
        description="使用的 LLM 模型"
    )

class GenerateResponse(BaseModel):
    """项目生成响应模型"""
    
    project_id: str
    status: str
    message: str
```

#### 1.4 响应模型 - `packages/projectgen-server/src/models/response.py`

```python
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

class StageStatus(BaseModel):
    """阶段状态"""
    status: str  # pending, running, completed, failed
    progress: int
    message: Optional[str] = None

class TaskStatus(BaseModel):
    """任务状态"""
    id: str
    status: str
    progress: int
    current_stage: str
    stages: Dict[str, StageStatus]
    created_at: str
    updated_at: str
    config: Dict[str, Any]
    logs: List[Dict[str, str]]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ProjectResult(BaseModel):
    """项目生成结果"""
    arch_design: str
    skeleton_design: str
    generated_files: List[Dict[str, str]]
    stats: Dict[str, int]
```

---

### 2. VSCode 插件扩展

#### 2.1 SlashCommand - `packages/projectgen-vscode-plugin/src/projectgen-command.ts`

```typescript
import { ContinueSDK, SlashCommand } from "core";
import { ProjectGenAPIClient } from "./api-client";
import * as vscode from "vscode";
import * as path from "path";

export const projectgenCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a new project using multi-agent framework",
  
  run: async function* (sdk: ContinueSDK) {
    const { ide, input } = sdk;
    
    try {
      // 1. 显示开始信息
      yield "🚀 **ProjectGen** - Multi-Agent Project Generation\n\n";
      
      // 2. 解析配置
      const config = await parseConfig(ide, input);
      if (!config) {
        yield "❌ Configuration cancelled or invalid.";
        return;
      }
      
      // 3. 显示配置信息
      yield `📋 **Configuration:**\n`;
      yield `- Dataset: \`${config.dataset}\`\n`;
      yield `- Repository: \`${config.repo_name}\`\n`;
      yield `- Model: \`${config.model}\`\n\n`;
      
      // 4. 检查服务器连接
      yield "🔌 Checking server connection...\n";
      const client = new ProjectGenAPIClient();
      const isHealthy = await client.checkHealth();
      
      if (!isHealthy) {
        yield "\n❌ **Error**: ProjectGen server is not running.\n\n";
        yield "Please start the server first:\n";
        yield "```bash\n";
        yield "cd packages/projectgen-server\n";
        yield "python src/main.py\n";
        yield "```\n";
        return;
      }
      
      yield "✅ Server connected\n\n";
      
      // 5. 启动生成任务
      yield "📤 Starting generation task...\n";
      const { project_id } = await client.startGeneration(config);
      yield `🆔 Project ID: \`${project_id}\`\n\n`;
      
      // 6. 显示进度条
      yield "📊 **Generation Progress:**\n\n";
      
      // 7. 通过 WebSocket 接收实时更新
      let lastStage = "";
      let lastProgress = 0;
      
      for await (const update of client.connectWebSocket(project_id)) {
        const { status, progress, current_stage, stages, error, result } = update;
        
        // 显示当前阶段
        if (current_stage !== lastStage) {
          const emoji = getStageEmoji(current_stage);
          yield `\n${emoji} **${formatStageName(current_stage)}**\n`;
          lastStage = current_stage;
        }
        
        // 显示进度（避免重复）
        if (progress > lastProgress) {
          const progressBar = generateProgressBar(progress);
          yield `${progressBar} ${progress}%\n`;
          lastProgress = progress;
        }
        
        // 显示详细阶段状态
        if (stages) {
          for (const [stage, stageData] of Object.entries(stages)) {
            if (stageData.status === "completed") {
              yield `  ✓ ${formatStageName(stage)} completed\n`;
            }
          }
        }
        
        // 检查完成状态
        if (status === "completed") {
          yield "\n🎉 **Generation Completed!**\n\n";
          
          // 8. 应用生成的代码
          if (result) {
            yield "📝 Applying generated code to workspace...\n";
            const appliedFiles = await applyGeneratedCode(ide, config, result);
            
            yield `\n✅ Applied ${appliedFiles} files to workspace\n`;
            yield `📁 Output directory: \`${config.dataset}_outputs/${config.repo_name}\`\n\n`;
            
            // 9. 显示统计信息
            if (result.stats) {
              yield "📊 **Statistics:**\n";
              yield `- Architecture iterations: ${result.stats.arch_iterations}\n`;
              yield `- Skeleton iterations: ${result.stats.skeleton_iterations}\n`;
              yield `- Code iterations: ${result.stats.code_iterations}\n\n`;
            }
          }
          
          yield "🎯 **Next Steps:**\n";
          yield "- Review generated files in the output directory\n";
          yield "- Use `/projectgen-memory` to view generation context\n";
          yield "- Run tests to validate the generated code\n";
          
          break;
        }
        
        if (status === "failed") {
          yield `\n❌ **Generation Failed**\n`;
          yield `Error: ${error}\n`;
          break;
        }
      }
      
    } catch (error: any) {
      yield `\n❌ **Unexpected Error:** ${error.message}\n`;
      console.error("ProjectGen command error:", error);
    }
  }
};

// ============= 辅助函数 =============

function getStageEmoji(stage: string): string {
  const emojiMap: Record<string, string> = {
    "initialization": "🔧",
    "architecture": "🏗️",
    "skeleton": "🦴",
    "code": "💻",
    "refinement": "✨",
    "completed": "🎉",
    "failed": "❌"
  };
  return emojiMap[stage] || "⚙️";
}

function formatStageName(stage: string): string {
  return stage
    .split("_")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function generateProgressBar(progress: number, width: number = 20): string {
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  return `[${"█".repeat(filled)}${"░".repeat(empty)}]`;
}

async function parseConfig(ide: any, input: string): Promise<any> {
  // 解析命令输入
  // 支持格式：/projectgen dataset=CodeProjectEval repo=bplustree model=gpt-4o
  
  const params: any = {};
  const matches = input.matchAll(/(\w+)=(\S+)/g);
  
  for (const match of matches) {
    params[match[1]] = match[2];
  }
  
  // 必需参数检查
  if (!params.repo && !params.repo_name) {
    throw new Error("Missing required parameter: repo or repo_name");
  }
  
  const dataset = params.dataset || "CodeProjectEval";
  const repoName = params.repo || params.repo_name;
  const model = params.model || "gpt-4o";
  
  // 读取 PRD 文件
  const workspaceRoot = ide.getWorkspaceRoot?.() || process.cwd();
  const repoPath = path.join(workspaceRoot, "datasets", dataset, repoName);
  
  let requirement = "";
  try {
    const prdPath = path.join(repoPath, "PRD.md");
    requirement = await ide.readFile(prdPath);
  } catch (e) {
    throw new Error(`Cannot read PRD file for ${repoName}. Path: ${repoPath}`);
  }
  
  return {
    dataset,
    repo_name: repoName,
    requirement,
    model
  };
}

async function applyGeneratedCode(
  ide: any,
  config: any,
  result: any
): Promise<number> {
  const workspaceRoot = ide.getWorkspaceRoot?.() || process.cwd();
  const outputDir = path.join(
    workspaceRoot,
    `${config.dataset}_outputs`,
    config.repo_name
  );
  
  let fileCount = 0;
  
  if (result.generated_files) {
    for (const file of result.generated_files) {
      const filePath = path.join(outputDir, file.path);
      await ide.writeFile(filePath, file.content);
      fileCount++;
    }
  }
  
  return fileCount;
}
```

#### 2.2 API 客户端 - `packages/projectgen-vscode-plugin/src/api-client.ts`

```typescript
import WebSocket from "ws";

export interface GenerateConfig {
  dataset: string;
  repo_name: string;
  requirement: string;
  uml_class?: string;
  code_file_dag?: string[];
  model: string;
}

export interface GenerateResponse {
  project_id: string;
  status: string;
  message: string;
}

export interface TaskUpdate {
  id: string;
  status: string;
  progress: number;
  current_stage: string;
  stages: Record<string, any>;
  error?: string;
  result?: any;
}

export class ProjectGenAPIClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = "http://localhost:5000") {
    this.baseUrl = baseUrl;
  }
  
  /**
   * 检查服务器健康状态
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000)  // 5秒超时
      });
      return response.ok;
    } catch (error) {
      console.error("Health check failed:", error);
      return false;
    }
  }
  
  /**
   * 启动项目生成任务
   */
  async startGeneration(config: GenerateConfig): Promise<GenerateResponse> {
    const response = await fetch(`${this.baseUrl}/api/projects/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(config)
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Server error: ${response.statusText} - ${error}`);
    }
    
    return await response.json();
  }
  
  /**
   * 获取任务状态
   */
  async getStatus(projectId: string): Promise<TaskUpdate> {
    const response = await fetch(
      `${this.baseUrl}/api/projects/${projectId}/status`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }
    
    return await response.json();
  }
  
  /**
   * 连接 WebSocket 并流式接收更新
   */
  async* connectWebSocket(projectId: string): AsyncGenerator<TaskUpdate> {
    const wsUrl = this.baseUrl.replace("http", "ws");
    const ws = new WebSocket(`${wsUrl}/api/ws/${projectId}`);
    
    yield* this.streamWebSocket(ws);
  }
  
  /**
   * 从 WebSocket 流式读取数据
   */
  private async* streamWebSocket(ws: WebSocket): AsyncGenerator<TaskUpdate> {
    const queue: TaskUpdate[] = [];
    let done = false;
    let error: Error | null = null;
    
    // 设置事件监听
    ws.on("message", (data: string) => {
      try {
        const update = JSON.parse(data);
        queue.push(update);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    });
    
    ws.on("close", () => {
      done = true;
    });
    
    ws.on("error", (err) => {
      error = err as Error;
      done = true;
    });
    
    // 等待连接建立
    await new Promise<void>((resolve, reject) => {
      ws.on("open", () => resolve());
      ws.on("error", reject);
    });
    
    // 流式返回数据
    while (!done || queue.length > 0) {
      if (error) {
        throw error;
      }
      
      if (queue.length > 0) {
        yield queue.shift()!;
      } else {
        // 等待新数据
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    // 关闭连接
    ws.close();
  }
  
  /**
   * 获取记忆内容
   */
  async getMemory(projectId: string, stage: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/projects/${projectId}/memory/${stage}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to get memory: ${response.statusText}`);
    }
    
    return await response.json();
  }
}
```

#### 2.3 类型定义 - `packages/projectgen-vscode-plugin/src/types.ts`

```typescript
export interface ProjectGenConfig {
  serverUrl: string;
  timeout: number;
  autoApply: boolean;
}

export interface StageInfo {
  name: string;
  description: string;
  emoji: string;
}

export const STAGES: Record<string, StageInfo> = {
  initialization: {
    name: "Initialization",
    description: "Preparing the generation environment",
    emoji: "🔧"
  },
  architecture: {
    name: "Architecture Design",
    description: "Designing system architecture and SSAT",
    emoji: "🏗️"
  },
  skeleton: {
    name: "Skeleton Generation",
    description: "Generating file structure and function signatures",
    emoji: "🦴"
  },
  code: {
    name: "Code Implementation",
    description: "Filling in function implementations",
    emoji: "💻"
  },
  refinement: {
    name: "Refinement",
    description: "Iterative improvement based on feedback",
    emoji: "✨"
  }
};
```

---

### 3. 注册到 Continue

#### 3.1 修改 Continue 扩展入口

在 `continue/extensions/vscode/src/extension.ts` 中注册 ProjectGen 命令：

```typescript
// 在文件顶部导入
import { projectgenCommand } from "../../../packages/projectgen-vscode-plugin/src/projectgen-command";

// 在 activateExtension 函数中添加
export async function activateExtension(context: vscode.ExtensionContext) {
  // ... 现有代码 ...
  
  // 注册 ProjectGen SlashCommand
  // 这里需要根据 Continue 的实际 API 调整
  // 示例：
  registerSlashCommand(projectgenCommand);
  
  console.log("ProjectGen command registered");
  
  // ... 其他初始化 ...
}
```

---

## 🔌 通信协议

### HTTP Endpoints

#### 1. POST `/api/projects/generate`

**请求**：
```json
{
  "dataset": "CodeProjectEval",
  "repo_name": "bplustree",
  "requirement": "Implement a B+ tree...",
  "uml_class": "...",
  "model": "gpt-4o"
}
```

**响应**：
```json
{
  "project_id": "uuid-xxx",
  "status": "started",
  "message": "Project generation started"
}
```

#### 2. GET `/api/projects/{id}/status`

**响应**：
```json
{
  "id": "uuid-xxx",
  "status": "running",
  "progress": 45,
  "current_stage": "skeleton",
  "stages": {
    "architecture": {
      "status": "completed",
      "progress": 100
    },
    "skeleton": {
      "status": "running",
      "progress": 60
    },
    "code": {
      "status": "pending",
      "progress": 0
    }
  },
  "created_at": "2026-01-14T10:00:00",
  "updated_at": "2026-01-14T10:05:30"
}
```

#### 3. WebSocket `/api/ws/{id}`

**消息格式**（服务器 → 客户端）：
```json
{
  "id": "uuid-xxx",
  "status": "running",
  "progress": 65,
  "current_stage": "code",
  "stages": { ... },
  "logs": [
    {
      "timestamp": "2026-01-14T10:05:00",
      "stage": "code",
      "message": "Generating file: main.py"
    }
  ]
}
```

---

## 🚀 部署方案

### 开发环境

```bash
# 1. 安装 Python 依赖
cd packages/projectgen-core
pip install -e .

cd ../projectgen-server
pip install -r requirements.txt

# 2. 启动服务器
python src/main.py
# 输出: Server running on http://localhost:5000

# 3. 编译 VSCode 插件
cd ../../continue/extensions/vscode
npm install
npm run compile

# 4. 启动调试（F5 in VSCode）
```

### 生产环境 - Docker

```dockerfile
# packages/projectgen-server/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ ./src/
COPY ../projectgen-core/src/projectgen ./projectgen-core/

# 暴露端口
EXPOSE 5000

# 启动服务
CMD ["python", "src/main.py"]
```

```bash
# 构建镜像
docker build -t projectgen-server:latest -f packages/projectgen-server/Dockerfile .

# 运行容器
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=xxx \
  projectgen-server:latest
```

### 配置管理

用户可以在 VSCode settings.json 中配置：

```json
{
  "projectgen.serverUrl": "http://localhost:5000",
  "projectgen.timeout": 600000,
  "projectgen.autoApply": true,
  "projectgen.model": "gpt-4o"
}
```

---

## 📅 实施路线图

### Phase 1: 基础框架（Week 1-2）

- [ ] 创建 packages 目录结构
- [ ] 重构 projectgen-core 为独立包
- [ ] 创建 FastAPI 服务器骨架
- [ ] 实现基本的 HTTP API
- [ ] 测试核心工作流调用

**交付物**：
- 可运行的 HTTP 服务器
- 基本的健康检查和状态查询

### Phase 2: 插件集成（Week 3-4）

- [ ] 创建 projectgen-vscode-plugin 包
- [ ] 实现 SlashCommand
- [ ] 实现 API 客户端
- [ ] 注册到 Continue 框架
- [ ] 基础 UI 反馈

**交付物**：
- 可在 Continue Chat 中调用的 /projectgen 命令
- 显示基本生成进度

### Phase 3: 实时通信（Week 5）

- [ ] 实现 WebSocket 服务端
- [ ] 实现 WebSocket 客户端
- [ ] 流式进度更新
- [ ] 详细阶段状态展示

**交付物**：
- 实时显示生成进度
- 各阶段状态可视化

### Phase 4: 完善功能（Week 6-7）

- [ ] 文件应用到工作区
- [ ] ContextProvider 实现
- [ ] 记忆查看功能
- [ ] 错误处理和重试
- [ ] 日志记录

**交付物**：
- 完整的端到端流程
- 稳定的错误处理

### Phase 5: 优化与测试（Week 8）

- [ ] 性能优化
- [ ] 单元测试
- [ ] 集成测试
- [ ] 文档完善
- [ ] Docker 镜像

**交付物**：
- 生产就绪的系统
- 完整文档

---

## ⚠️ 风险与挑战

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Continue API 变更 | 高 | 版本锁定，关注官方更新 |
| WebSocket 稳定性 | 中 | 实现重连机制，降级到轮询 |
| Python-Node 通信 | 中 | 充分测试，完善错误处理 |
| 大模型 API 限流 | 高 | 实现重试、队列管理 |
| 长时间任务超时 | 中 | 设置合理超时，支持恢复 |

### 实施风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 开发周期延长 | 中 | 分阶段交付，MVP 优先 |
| 用户学习成本 | 低 | 详细文档，示例演示 |
| 部署复杂度 | 中 | 提供 Docker 镜像 |
| 维护成本 | 中 | 良好的代码组织和文档 |

---

## 📚 参考资料

- [Continue Documentation](https://docs.continue.dev)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [VSCode Extension API](https://code.visualstudio.com/api)
- [WebSocket Protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

---

## 📝 附录

### A. 环境要求

**前端**：
- Node.js >= 18.0
- npm >= 9.0
- VSCode >= 1.70.0

**后端**：
- Python >= 3.9
- pip >= 21.0
- 4GB+ RAM（建议 8GB）

### B. 依赖清单

**Python**：
```txt
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
langchain>=0.1.0
langgraph>=0.0.1
openai>=1.0.0
websockets>=12.0
```

**TypeScript**：
```json
{
  "dependencies": {
    "ws": "^8.14.0"
  },
  "devDependencies": {
    "@types/ws": "^8.5.0",
    "typescript": "^5.0.0"
  }
}
```

---

**文档版本**: 1.0  
**最后更新**: 2026年1月14日  
**作者**: ProjectGen Team
