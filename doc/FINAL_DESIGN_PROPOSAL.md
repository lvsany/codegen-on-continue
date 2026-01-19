# ProjectGen × Continue 集成方案 - 最终设计提案

**版本**: 3.0 (针对 new-projectgen 项目定制)  
**日期**: 2026年1月19日  
**状态**: 待审核

---

## 📊 项目现状分析

### new-projectgen 项目特点

基于对你的项目代码的分析，ProjectGen 具有以下核心特征：

#### 1. **三阶段多智能体工作流**

```python
# workflow.py 中的核心流程
architecture → arch_judge → (迭代或进入下一阶段)
skeleton → skeleton_judge → (迭代或进入下一阶段)  
code → code_judge → (迭代或结束)
```

**特点**：
- 每个阶段都有生成 Agent 和评判 Agent
- 支持迭代优化（最多 3-5 次）
- 使用 LangGraph 编排工作流

#### 2. **复杂的数据结构**

- **SSAT (Semantic Software Architecture Tree)**: 层次化的架构表示
- **Skeleton Code**: 函数签名和类结构
- **Complete Code**: 完整实现
- **JSON Schema 验证**: 所有输出都有严格的 schema

#### 3. **记忆管理系统**

```
memory_manager/
├── arch_memory.py      # 架构阶段记忆
├── skeleton_memory.py  # 骨架阶段记忆
├── code_memory.py      # 代码阶段记忆
└── code_shared_memory.py  # 跨文件共享记忆
```

**特点**：
- 每个阶段维护独立的记忆
- 支持上下文检索和相关性排序
- 用于迭代时的反馈整合

#### 4. **数据集驱动**

```python
# main.py 中的批处理逻辑
for repo_name in repo_list:
    # 读取 config.json
    # 读取 PRD.md, UML, architecture_design.md
    # 执行生成
    # 保存到 {dataset}_outputs/{model}/{repo_name}/
```

**特点**：
- 支持 CodeProjectEval 和 DevBench 数据集
- 每个 repo 有独立的配置文件
- 批量处理多个项目

#### 5. **测试驱动的迭代**

```python
# code_judge_agent.py
# 执行 check_tests 验证生成的代码
# 根据测试结果提供反馈
# 触发代码修复迭代
```

---

## 🎯 集成目标与约束

### 核心目标

1. **在 Continue Chat 中触发项目生成**
   - 用户输入：`/projectgen repo=bplustree dataset=CodeProjectEval`
   - 自动读取数据集配置
   - 启动多智能体工作流

2. **实时显示生成进度**
   - 当前阶段（architecture/skeleton/code）
   - 迭代次数
   - 评分和反馈摘要

3. **生成结果自动应用到工作区**
   - 创建输出目录
   - 写入生成的代码文件
   - 显示统计信息

4. **支持记忆查看**（可选）
   - 通过 ContextProvider 查看各阶段记忆
   - 辅助调试和理解生成过程

### 关键约束

1. **不破坏现有工作流**
   - `workflow.py` 和 agents 保持不变
   - 只添加 HTTP 接口层

2. **最小化 Continue 源码修改**
   - 只添加一个 SlashCommand
   - 不修改 Continue 核心逻辑

3. **支持本地和远程部署**
   - 开发时本地运行
   - 生产环境可 Docker 化

4. **保持现有的批处理能力**
   - `main.py` 仍可独立运行
   - FastAPI 服务器是可选的接口

---

## 🏗️ 架构设计（最终版）

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Continue VSCode Extension (修改)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  SlashCommand: /projectgen                            │  │
│  │  - 解析参数 (repo, dataset, model)                   │  │
│  │  - 读取数据集配置                                     │  │
│  │  - 调用 FastAPI 服务器                               │  │
│  │  - 轮询进度并显示                                     │  │
│  │  - 应用生成的代码到工作区                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    ↕ HTTP (POST/GET)
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Server (新增)                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HTTP Endpoints                                        │  │
│  │  - POST /api/generate                                 │  │
│  │  - GET  /api/status/{project_id}                      │  │
│  │  - GET  /api/memory/{project_id}/{stage}              │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Workflow Wrapper                                      │  │
│  │  - 调用 build_graph()                                 │  │
│  │  - 监听工作流事件                                     │  │
│  │  - 更新任务状态                                       │  │
│  │  - 提取记忆内容                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    ↕ 直接调用
┌─────────────────────────────────────────────────────────────┐
│  ProjectGen Core (保持不变)                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  workflow.py: LangGraph 工作流                        │  │
│  │  agents/: 6个智能体                                   │  │
│  │  memory_manager/: 记忆管理                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入 → Continue SlashCommand
    ↓
读取数据集配置 (PRD.md, UML, architecture_design.md)
    ↓
POST /api/generate {repo_name, dataset, requirement, ...}
    ↓
FastAPI 创建任务 → 异步启动 workflow
    ↓
LangGraph 执行: architecture → skeleton → code
    ↓ (每个阶段更新状态)
GET /api/status/{project_id} (轮询)
    ↓
返回: {stage, progress, iteration, score, ...}
    ↓
Continue 显示进度条和日志
    ↓
任务完成 → 返回生成的文件列表
    ↓
Continue 写入文件到工作区
```

---

## 📁 项目结构（最终版）

```
new-projectgen/
├── src/                                    # ProjectGen 核心（不修改）
│   ├── agents/
│   ├── memory_manager/
│   ├── workflow.py
│   ├── main.py                             # 保留批处理能力
│   └── ...
│
├── projectgen-server/                      # FastAPI 服务器（新增）
│   ├── main.py                             # 服务器入口
│   ├── workflow_wrapper.py                 # 工作流包装器
│   ├── models.py                           # Pydantic 模型
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── continue/                               # Continue 框架（最小修改）
│   └── core/
│       └── commands/slash/built-in-legacy/
│           ├── index.ts                    # 修改：注册 projectgen
│           └── projectgen.ts               # 新增：SlashCommand 实现
│
├── datasets/                               # 数据集（保持不变）
│   ├── CodeProjectEval/
│   └── DevBench/
│
└── doc/                                    # 文档
    ├── integration-design-REVISED.md
    ├── IMPLEMENTATION_GUIDE.md
    ├── PROBLEMS_SUMMARY.md
    └── FINAL_DESIGN_PROPOSAL.md            # 本文档
```

---

## 🔧 核心组件设计

### 1. FastAPI 服务器 - `projectgen-server/main.py`

#### 关键改进点

**与之前设计的区别**：
1. **真实集成 workflow.py**（不是模拟）
2. **支持数据集配置读取**
3. **提取真实的记忆内容**
4. **支持迭代进度跟踪**

```python
# projectgen-server/main.py (核心逻辑)

from fastapi import FastAPI
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from workflow import build_graph
from memory_manager.arch_memory import ArchMemory
from memory_manager.skeleton_memory import SkeletonMemory
from memory_manager.code_memory import CodeMemory

app = FastAPI()

# 全局工作流实例
workflow_graph = None

def get_workflow():
    global workflow_graph
    if workflow_graph is None:
        workflow_graph = build_graph()
    return workflow_graph

@app.post("/api/generate")
async def generate_project(request: GenerateRequest):
    """
    启动项目生成
    
    关键改进：
    1. 读取数据集配置（config.json, PRD.md, UML, architecture_design.md）
    2. 准备 initial_state（与 main.py 一致）
    3. 异步执行 workflow
    4. 监听工作流事件更新进度
    """
    project_id = str(uuid.uuid4())
    
    # 读取数据集配置
    repo_dir = f"../datasets/{request.dataset}/{request.repo_name}"
    config = json.load(open(f"{repo_dir}/config.json"))
    
    requirement = open(f"{repo_dir}/{config['PRD']}").read()
    uml_class = open(f"{repo_dir}/{config['UML'][0]}").read() if config.get('UML') else ""
    arch_design = open(f"{repo_dir}/{config['architecture_design']}").read()
    code_file_dag = config.get('code_file_DAG', [])
    
    # 初始化任务
    tasks[project_id] = {
        "id": project_id,
        "status": "running",
        "current_stage": "architecture",
        "stages": {
            "architecture": {"iteration": 0, "score": 0, "status": "running"},
            "skeleton": {"iteration": 0, "score": 0, "status": "pending"},
            "code": {"iteration": 0, "score": 0, "status": "pending"}
        },
        "config": request.dict(),
        "logs": []
    }
    
    # 异步执行工作流
    asyncio.create_task(run_workflow(project_id, {
        "user_input": requirement,
        "uml_class": uml_class,
        "arch_design": arch_design,
        "repo_name": request.repo_name,
        "code_file_DAG": code_file_dag,
        "repo_dir": f"../outputs/{project_id}",
        "dataset": request.dataset
    }))
    
    return {"project_id": project_id, "status": "started"}

async def run_workflow(project_id: str, initial_state: dict):
    """
    执行工作流并更新任务状态
    
    关键：使用 LangGraph 的回调机制监听事件
    """
    try:
        graph = get_workflow()
        
        # 使用回调监听工作流事件
        final_state = await asyncio.to_thread(
            graph.invoke,
            initial_state,
            config={
                "recursion_limit": 50,
                "callbacks": [WorkflowProgressCallback(project_id)]
            }
        )
        
        # 提取生成的文件
        output_dir = initial_state["repo_dir"]
        generated_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, output_dir)
                    content = open(file_path).read()
                    generated_files.append({"path": rel_path, "content": content})
        
        tasks[project_id]["status"] = "completed"
        tasks[project_id]["result"] = {
            "generated_files": generated_files,
            "stats": {
                "arch_iterations": final_state.get("arch_steps", 0),
                "skeleton_iterations": final_state.get("skeleton_steps", 0),
                "code_iterations": final_state.get("code_steps", 0)
            }
        }
        
    except Exception as e:
        tasks[project_id]["status"] = "failed"
        tasks[project_id]["error"] = str(e)

class WorkflowProgressCallback:
    """LangGraph 回调，用于更新任务进度"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
    
    def on_agent_action(self, action, **kwargs):
        """当 Agent 执行动作时调用"""
        agent_name = action.get("agent")
        
        if "architecture" in agent_name:
            stage = "architecture"
        elif "skeleton" in agent_name:
            stage = "skeleton"
        elif "code" in agent_name:
            stage = "code"
        else:
            return
        
        # 更新当前阶段
        tasks[self.project_id]["current_stage"] = stage
        tasks[self.project_id]["stages"][stage]["status"] = "running"
        
        # 如果是 judge agent，提取评分
        if "judge" in agent_name and "score" in action:
            score = action["score"]
            tasks[self.project_id]["stages"][stage]["score"] = score
            tasks[self.project_id]["stages"][stage]["iteration"] += 1

@app.get("/api/memory/{project_id}/{stage}")
async def get_memory(project_id: str, stage: str):
    """
    获取记忆内容
    
    关键改进：从真实的 memory_manager 中读取
    """
    if project_id not in tasks:
        raise HTTPException(404, "Project not found")
    
    task = tasks[project_id]
    repo_dir = f"../outputs/{project_id}"
    
    # 根据阶段读取对应的记忆
    if stage == "architecture":
        memory = ArchMemory(repo_dir)
        content = memory.get_all_memories()
    elif stage == "skeleton":
        memory = SkeletonMemory(repo_dir)
        content = memory.get_all_memories()
    elif stage == "code":
        memory = CodeMemory(repo_dir)
        content = memory.get_all_memories()
    else:
        content = "Unknown stage"
    
    return {
        "project_id": project_id,
        "stage": stage,
        "memory": content
    }
```

### 2. Continue SlashCommand - `continue/core/commands/slash/built-in-legacy/projectgen.ts`

#### 关键改进点

**与之前设计的区别**：
1. **自动读取数据集配置**
2. **显示详细的阶段信息**（迭代次数、评分）
3. **更好的错误处理**
4. **支持取消任务**

```typescript
import { SlashCommand } from "../../../index.js";

const ProjectGenSlashCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a project using multi-agent framework (architecture → skeleton → code)",
  
  run: async function* ({ ide, input, params }) {
    const serverUrl = params?.serverUrl || "http://localhost:5000";
    
    try {
      yield "🚀 **ProjectGen** - Multi-Agent Project Generation\n\n";
      
      // 1. 解析参数
      const config = parseInput(input, params);
      if (!config.repo_name) {
        yield "❌ **Error**: Missing required parameter 'repo'\n\n";
        yield "**Usage**:\n";
        yield "```\n";
        yield "/projectgen repo=<name> [dataset=CodeProjectEval] [model=gpt-4o]\n";
        yield "```\n\n";
        yield "**Example**:\n";
        yield "```\n";
        yield "/projectgen repo=bplustree dataset=CodeProjectEval model=gpt-4o\n";
        yield "```\n";
        return;
      }
      
      yield `📋 **Configuration**:\n`;
      yield `- Repository: \`${config.repo_name}\`\n`;
      yield `- Dataset: \`${config.dataset}\`\n`;
      yield `- Model: \`${config.model}\`\n\n`;
      
      // 2. 验证数据集存在
      const workspaceDir = ide.getWorkspaceDirectory();
      const repoDir = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}`;
      
      try {
        await ide.readFile(`${repoDir}/config.json`);
      } catch (e) {
        yield `❌ **Error**: Repository not found at \`${repoDir}\`\n`;
        yield `Please ensure the dataset exists.\n`;
        return;
      }
      
      yield "✅ Repository found\n\n";
      
      // 3. 检查服务器
      yield "🔌 Connecting to ProjectGen server...\n";
      try {
        const healthCheck = await fetch(`${serverUrl}/api/health`, {
          signal: AbortSignal.timeout(5000)
        });
        if (!healthCheck.ok) throw new Error("Server not healthy");
      } catch (e) {
        yield "❌ **Error**: ProjectGen server is not running\n\n";
        yield "**Please start the server**:\n";
        yield "```bash\n";
        yield "cd projectgen-server\n";
        yield "python main.py\n";
        yield "```\n";
        return;
      }
      yield "✅ Server connected\n\n";
      
      // 4. 启动生成任务
      yield "📤 Starting generation task...\n";
      const startResponse = await fetch(`${serverUrl}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_name: config.repo_name,
          dataset: config.dataset,
          model: config.model
        })
      });
      
      if (!startResponse.ok) {
        const error = await startResponse.text();
        yield `❌ **Error**: ${error}\n`;
        return;
      }
      
      const { project_id } = await startResponse.json();
      yield `🆔 Project ID: \`${project_id}\`\n\n`;
      
      // 5. 显示三阶段流程图
      yield "📊 **Generation Workflow**:\n\n";
      yield "```\n";
      yield "┌─────────────┐     ┌─────────────┐     ┌─────────────┐\n";
      yield "│Architecture │ ──> │  Skeleton   │ ──> │    Code     │\n";
      yield "│   Design    │     │ Generation  │     │  Filling    │\n";
      yield "└─────────────┘     └─────────────┘     └─────────────┘\n";
      yield "     ↓ Judge             ↓ Judge             ↓ Judge\n";
      yield "   (迭代优化)           (迭代优化)           (迭代优化)\n";
      yield "```\n\n";
      
      // 6. 轮询进度
      yield "⏳ **Progress**:\n\n";
      
      let lastStage = "";
      let lastIteration = { architecture: 0, skeleton: 0, code: 0 };
      let isComplete = false;
      
      while (!isComplete) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const statusResponse = await fetch(
          `${serverUrl}/api/status/${project_id}`
        );
        const status = await statusResponse.json();
        
        const currentStage = status.current_stage;
        const stageInfo = status.stages[currentStage];
        
        // 阶段切换时显示标题
        if (currentStage !== lastStage) {
          const emoji = getStageEmoji(currentStage);
          yield `\n${emoji} **${formatStageName(currentStage)}**\n`;
          lastStage = currentStage;
        }
        
        // 显示迭代信息
        if (stageInfo && stageInfo.iteration > lastIteration[currentStage]) {
          const iteration = stageInfo.iteration;
          const score = stageInfo.score || 0;
          yield `  - Iteration ${iteration}: Score ${score}/10\n`;
          lastIteration[currentStage] = iteration;
          
          // 如果评分通过，显示完成
          if (score >= 8) {
            yield `  ✓ ${formatStageName(currentStage)} completed (passed)\n`;
          }
        }
        
        // 检查完成状态
        if (status.status === "completed") {
          yield "\n🎉 **Generation Completed!**\n\n";
          
          // 应用生成的代码
          if (status.result?.generated_files) {
            yield "📝 Applying generated code to workspace...\n";
            const outputDir = `${workspaceDir}/${config.dataset}_outputs/${config.repo_name}`;
            
            let fileCount = 0;
            for (const file of status.result.generated_files) {
              const filePath = `${outputDir}/${file.path}`;
              await ide.writeFile(filePath, file.content);
              fileCount++;
            }
            
            yield `✅ Applied ${fileCount} files\n`;
            yield `📁 Output: \`${config.dataset}_outputs/${config.repo_name}\`\n\n`;
            
            // 显示统计
            if (status.result.stats) {
              yield "📊 **Statistics**:\n";
              yield `- Architecture iterations: ${status.result.stats.arch_iterations}\n`;
              yield `- Skeleton iterations: ${status.result.stats.skeleton_iterations}\n`;
              yield `- Code iterations: ${status.result.stats.code_iterations}\n\n`;
            }
            
            // 下一步建议
            yield "🎯 **Next Steps**:\n";
            yield `- Review files in \`${config.dataset}_outputs/${config.repo_name}\`\n`;
            yield `- Run tests: \`cd ${config.dataset}_outputs/${config.repo_name} && pytest\`\n`;
            yield `- View memory: \`/projectgen-memory ${project_id} architecture\`\n`;
          }
          
          isComplete = true;
        } else if (status.status === "failed") {
          yield `\n❌ **Generation Failed**\n`;
          yield `Error: ${status.error}\n`;
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

export default ProjectGenSlashCommand;
```

---

## 🔄 工作流集成策略

### 关键问题：如何监听 LangGraph 工作流事件？

**方案 1: 使用 LangGraph 的回调机制**（推荐）

```python
# LangGraph 支持回调
from langchain.callbacks.base import BaseCallbackHandler

class ProgressCallback(BaseCallbackHandler):
    def __init__(self, project_id):
        self.project_id = project_id
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        # 检测阶段切换
        pass
    
    def on_chain_end(self, outputs, **kwargs):
        # 提取评分和反馈
        pass

# 在 invoke 时传入
final_state = graph.invoke(
    initial_state,
    config={"callbacks": [ProgressCallback(project_id)]}
)
```

**方案 2: 修改 workflow.py 添加钩子**（侵入性更小）

```python
# workflow.py 中添加进度回调
def build_graph(progress_callback=None):
    # ... 现有代码 ...
    
    def wrapped_architecture(state):
        if progress_callback:
            progress_callback("architecture", "start", state)
        result = architecture_agent(state)
        if progress_callback:
            progress_callback("architecture", "end", result)
        return result
    
    builder.add_node("architecture", wrapped_architecture)
    # ... 其他节点类似 ...
```

**方案 3: 轮询状态文件**（最简单，但不够优雅）

```python
# 在 agents 中写入状态文件
# projectgen-server 定期读取
status_file = f"{repo_dir}/status.json"
json.dump({"stage": "architecture", "iteration": 1}, open(status_file, "w"))
```

**推荐**: 使用**方案 1**（LangGraph 回调），因为：
- 不需要修改现有代码
- 实时性最好
- 符合 LangGraph 的设计理念

---

## 📊 进度显示设计

### Continue Chat 中的显示效果

```
🚀 ProjectGen - Multi-Agent Project Generation

📋 Configuration:
- Repository: `bplustree`
- Dataset: `CodeProjectEval`
- Model: `gpt-4o`

✅ Repository found
✅ Server connected

📤 Starting generation task...
🆔 Project ID: `abc-123-def`

📊 Generation Workflow:

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│Architecture │ ──> │  Skeleton   │ ──> │    Code     │
│   Design    │     │ Generation  │     │  Filling    │
└─────────────┘     └─────────────┘     └─────────────┘
     ↓ Judge             ↓ Judge             ↓ Judge
   (迭代优化)           (迭代优化)           (迭代优化)

⏳ Progress:

🏗️ Architecture Design
  - Iteration 1: Score 7/10
  - Iteration 2: Score 9/10
  ✓ Architecture Design completed (passed)

🦴 Skeleton Generation
  - Iteration 1: Score 8/10
  ✓ Skeleton Generation completed (passed)

💻 Code Implementation
  - Iteration 1: Score 6/10
  - Iteration 2: Score 7/10
  - Iteration 3: Score 9/10
  ✓ Code Implementation completed (passed)

🎉 Generation Completed!

📝 Applying generated code to workspace...
✅ Applied 8 files
📁 Output: `CodeProjectEval_outputs/bplustree`

📊 Statistics:
- Architecture iterations: 2
- Skeleton iterations: 1
- Code iterations: 3

🎯 Next Steps:
- Review files in `CodeProjectEval_outputs/bplustree`
- Run tests: `cd CodeProjectEval_outputs/bplustree && pytest`
- View memory: `/projectgen-memory abc-123-def architecture`
```

---

## 🎨 可选功能：记忆查看

### ContextProvider 实现

```typescript
// continue/core/context/providers/projectgen-memory.ts

export class ProjectGenMemoryProvider implements IContextProvider {
  get description(): ContextProviderDescription {
    return {
      title: "projectgen-memory",
      displayTitle: "ProjectGen Memory",
      description: "View memory from ProjectGen generation stages",
      type: "query"
    };
  }
  
  async getContextItems(
    query: string,
    extras: ContextProviderExtras
  ): Promise<ContextItem[]> {
    // query 格式: "project_id stage"
    // 例如: "abc-123-def architecture"
    
    const [projectId, stage] = query.split(" ");
    
    const response = await fetch(
      `http://localhost:5000/api/memory/${projectId}/${stage}`
    );
    const data = await response.json();
    
    return [{
      name: `${stage} Memory`,
      description: `Memory from ${stage} stage`,
      content: JSON.stringify(data.memory, null, 2)
    }];
  }
}
```

### 使用方式

在 Continue Chat 中：
```
@projectgen-memory abc-123-def architecture

Show me the architecture design decisions
```

---

## ⚖️ 方案对比与决策

### 方案 A: 修改 Continue 源码（当前方案）

**优点**：
- ✅ 完全控制，功能强大
- ✅ 用户体验最好（原生集成）
- ✅ 可以访问所有 Continue API

**缺点**：
- ❌ 需要维护 Continue 的 fork
- ❌ Continue 更新时需要手动合并
- ❌ 不能直接发布到 Marketplace（需要改名）

**适用场景**：
- 你的团队内部使用
- 需要深度定制
- 愿意维护 fork

### 方案 B: 使用 Continue 的 /http 命令

**优点**：
- ✅ 不需要修改 Continue 源码
- ✅ 快速验证概念
- ✅ 易于部署

**缺点**：
- ❌ 功能受限（无法显示实时进度）
- ❌ 用户体验较差
- ❌ 无法访问 IDE API（写文件等）

**适用场景**：
- 快速原型验证
- 临时解决方案

### 方案 C: 独立的 VSCode 扩展

**优点**：
- ✅ 完全独立，不依赖 Continue
- ✅ 可以发布到 Marketplace
- ✅ 更新和维护独立

**缺点**：
- ❌ 无法利用 Continue 的 Chat 界面
- ❌ 需要自己实现 UI
- ❌ 开发工作量大

**适用场景**：
- 想要独立产品
- 不依赖 Continue
- 有资源开发完整 UI

---

## 🎯 推荐方案

基于你的项目特点和需求，我推荐：

### **阶段 1: 快速验证（1-2天）**

使用**方案 B**（/http 命令）快速验证：
1. 实现基础的 FastAPI 服务器
2. 使用 Continue 的 /http 命令调用
3. 验证工作流集成是否正常

### **阶段 2: 完整实现（1-2周）**

切换到**方案 A**（修改 Continue 源码）：
1. 实现完整的 FastAPI 服务器（带回调）
2. 添加 ProjectGen SlashCommand
3. 实现进度显示和文件应用
4. （可选）添加记忆查看功能

### **阶段 3: 长期维护（持续）**

根据使用情况决定：
- 如果只是内部使用 → 继续维护 fork
- 如果想公开发布 → 考虑独立扩展（方案 C）

---

## ✅ 实施前检查清单

在开始编码之前，请确认以下问题：

### 技术决策

- [ ] **确认部署方式**: 本地开发 / Docker / 云服务器？
- [ ] **确认 Continue 修改策略**: Fork 并维护 / 使用 /http 命令？
- [ ] **确认工作流监听方案**: LangGraph 回调 / 修改 workflow.py / 状态文件？
- [ ] **确认进度更新方式**: HTTP 轮询 / WebSocket？

### 功能范围

- [ ] **核心功能**: 启动生成、显示进度、应用文件
- [ ] **可选功能**: 记忆查看、取消任务、重试失败？
- [ ] **批处理支持**: 是否需要支持批量生成多个 repo？

### 兼容性

- [ ] **保持 main.py 可用**: FastAPI 服务器是可选的
- [ ] **不破坏现有工作流**: agents 和 memory_manager 不修改
- [ ] **数据集兼容**: 支持 CodeProjectEval 和 DevBench

### 测试计划

- [ ] **单元测试**: FastAPI 端点测试
- [ ] **集成测试**: 完整工作流测试
- [ ] **用户测试**: 在 Continue Chat 中测试

---

## 📝 下一步行动

### 立即可以做的（不写代码）

1. **审查本设计文档**
   - 确认架构设计是否符合你的需求
   - 标记需要修改或澄清的部分
   - 确定功能优先级

2. **做出关键决策**
   - 选择实施方案（A/B/C）
   - 确定工作流监听策略
   - 决定功能范围

3. **准备环境**
   - 确认 Python 和 Node.js 版本
   - 克隆 Continue 仓库（如果选择方案 A）
   - 准备测试数据集

### 准备好后开始编码

1. **Phase 1**: 实现 FastAPI 服务器基础框架
2. **Phase 2**: 集成 workflow.py 和回调机制
3. **Phase 3**: 实现 Continue SlashCommand
4. **Phase 4**: 端到端测试和优化

---

## 🤔 需要你的反馈

在我开始编写代码之前，请回答以下问题：

1. **你更倾向于哪个方案**？
   - A: 修改 Continue 源码（功能完整）
   - B: 使用 /http 命令（快速验证）
   - C: 独立 VSCode 扩展（独立产品）

2. **你是否需要批处理支持**？
   - 在 Continue 中一次生成多个 repo？
   - 还是保持 main.py 的批处理能力就够了？

3. **记忆查看功能的优先级**？
   - 必须有（用于调试和理解）
   - 可选（后续添加）
   - 不需要

4. **部署环境**？
   - 本地开发（localhost）
   - Docker 容器
   - 云服务器（需要远程访问）

5. **是否需要支持 DevBench 数据集**？
   - 还是只关注 CodeProjectEval？

---

**请审查本设计文档，并告诉我你的决策和反馈。确认无误后，我将开始实施。**
