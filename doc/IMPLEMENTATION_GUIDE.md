# ProjectGen × Continue 实施指南

本指南提供了将 ProjectGen 集成到 Continue VSCode 插件的详细步骤。

---

## 📋 前置要求

### 环境要求

- **Python**: 3.9+
- **Node.js**: 18.0+
- **VSCode**: 1.70.0+
- **Git**: 用于克隆 Continue 仓库

### 技能要求

- 基础的 Python 和 TypeScript 知识
- 了解 FastAPI 和 VSCode 扩展开发
- 熟悉命令行操作

---

## 🚀 快速开始（5分钟）

### 步骤 1: 启动 ProjectGen Server

```bash
# 进入服务器目录
cd projectgen-server

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
```

你应该看到：
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:5000
```

### 步骤 2: 测试服务器

在另一个终端：

```bash
# 健康检查
curl http://localhost:5000/api/health

# 应该返回：
# {"status":"healthy","active_tasks":0,"total_tasks":0,"timestamp":"..."}
```

### 步骤 3: 测试生成 API

```bash
# 创建测试请求
curl -X POST http://localhost:5000/api/projects/generate \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "CodeProjectEval",
    "repo_name": "test-project",
    "requirement": "Create a simple calculator",
    "model": "gpt-4o"
  }'

# 返回：
# {"project_id":"xxx-xxx-xxx","status":"started","message":"..."}
```

### 步骤 4: 查询状态

```bash
# 使用上面返回的 project_id
curl http://localhost:5000/api/projects/{project_id}/status
```

---

## 🔧 完整实施步骤

### 方案 A: 修改 Continue 源码（推荐，功能完整）

#### 1. Fork 和克隆 Continue

```bash
# 如果还没有 fork，先在 GitHub 上 fork Continue 仓库
# https://github.com/continuedev/continue

# 克隆你的 fork
git clone https://github.com/YOUR_USERNAME/continue.git
cd continue

# 安装依赖
npm install
```

#### 2. 创建 ProjectGen SlashCommand

创建文件 `continue/core/commands/slash/built-in-legacy/projectgen.ts`:

```typescript
import { SlashCommand } from "../../../index.js";

interface ProjectGenConfig {
  dataset: string;
  repo_name: string;
  model: string;
}

const ProjectGenSlashCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a project using multi-agent framework",
  
  run: async function* ({ ide, input, params }) {
    const serverUrl = params?.serverUrl || "http://localhost:5000";
    
    try {
      yield "🚀 **ProjectGen** - Multi-Agent Project Generation\n\n";
      
      // 解析参数
      const config = parseInput(input, params);
      if (!config.repo_name) {
        yield "❌ Error: Missing required parameter 'repo'\n";
        yield "Usage: /projectgen repo=<name> [dataset=CodeProjectEval] [model=gpt-4o]\n";
        return;
      }
      
      yield `📋 Repository: \`${config.repo_name}\`\n`;
      yield `📦 Dataset: \`${config.dataset}\`\n`;
      yield `🤖 Model: \`${config.model}\`\n\n`;
      
      // 读取 PRD
      const workspaceDir = ide.getWorkspaceDirectory();
      const prdPath = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}/PRD.md`;
      
      let requirement: string;
      try {
        requirement = await ide.readFile(prdPath);
      } catch (e) {
        yield `❌ Error: Cannot read PRD file at ${prdPath}\n`;
        yield `Please ensure the file exists.\n`;
        return;
      }
      
      // 检查服务器
      yield "🔌 Checking server connection...\n";
      const healthCheck = await fetch(`${serverUrl}/api/health`);
      if (!healthCheck.ok) {
        yield "❌ Error: ProjectGen server is not running\n";
        yield `Please start: \`cd projectgen-server && python main.py\`\n`;
        return;
      }
      yield "✅ Server connected\n\n";
      
      // 启动生成
      yield "📤 Starting generation task...\n";
      const startResponse = await fetch(`${serverUrl}/api/projects/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset: config.dataset,
          repo_name: config.repo_name,
          requirement,
          model: config.model,
        }),
      });
      
      if (!startResponse.ok) {
        const error = await startResponse.text();
        yield `❌ Error: ${error}\n`;
        return;
      }
      
      const { project_id } = await startResponse.json();
      yield `🆔 Project ID: \`${project_id}\`\n\n`;
      yield "📊 **Progress:**\n\n";
      
      // 轮询状态
      let lastProgress = 0;
      let isComplete = false;
      
      while (!isComplete) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const statusResponse = await fetch(
          `${serverUrl}/api/projects/${project_id}/status`
        );
        const status = await statusResponse.json();
        
        if (status.progress > lastProgress) {
          const bar = generateProgressBar(status.progress);
          yield `${bar} ${status.progress}% - ${status.current_stage}\n`;
          lastProgress = status.progress;
        }
        
        if (status.status === "completed") {
          yield "\n🎉 **Generation Completed!**\n\n";
          
          // 应用生成的代码
          if (status.result?.generated_files) {
            yield "📝 Applying generated code to workspace...\n";
            const outputDir = `${workspaceDir}/${config.dataset}_outputs/${config.repo_name}`;
            
            for (const file of status.result.generated_files) {
              const filePath = `${outputDir}/${file.path}`;
              await ide.writeFile(filePath, file.content);
            }
            
            yield `✅ Applied ${status.result.generated_files.length} files\n`;
            yield `📁 Output directory: \`${config.dataset}_outputs/${config.repo_name}\`\n\n`;
            
            if (status.result.stats) {
              yield "📊 **Statistics:**\n";
              yield `- Architecture iterations: ${status.result.stats.arch_iterations}\n`;
              yield `- Skeleton iterations: ${status.result.stats.skeleton_iterations}\n`;
              yield `- Code iterations: ${status.result.stats.code_iterations}\n`;
            }
          }
          
          isComplete = true;
        } else if (status.status === "failed") {
          yield `\n❌ **Generation Failed**: ${status.error}\n`;
          isComplete = true;
        }
      }
      
    } catch (error: any) {
      yield `\n❌ **Unexpected Error**: ${error.message}\n`;
      console.error("ProjectGen error:", error);
    }
  }
};

function parseInput(input: string, params: any): ProjectGenConfig {
  const config: ProjectGenConfig = {
    dataset: params?.dataset || "CodeProjectEval",
    repo_name: "",
    model: params?.model || "gpt-4o",
  };
  
  const repoMatch = input.match(/repo=(\S+)/);
  if (repoMatch) config.repo_name = repoMatch[1];
  
  const datasetMatch = input.match(/dataset=(\S+)/);
  if (datasetMatch) config.dataset = datasetMatch[1];
  
  const modelMatch = input.match(/model=(\S+)/);
  if (modelMatch) config.model = modelMatch[1];
  
  return config;
}

function generateProgressBar(progress: number, width: number = 20): string {
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  return `[${"█".repeat(filled)}${"░".repeat(empty)}]`;
}

export default ProjectGenSlashCommand;
```

#### 3. 注册 SlashCommand

编辑 `continue/core/commands/slash/built-in-legacy/index.ts`:

```typescript
// 在文件顶部添加导入
import ProjectGenSlashCommand from "./projectgen.js";

// 在 LegacyBuiltInSlashCommands 数组中添加
const LegacyBuiltInSlashCommands: SlashCommand[] = [
  CmdSlashCommand,
  CommitMessageSlashCommand,
  DraftIssueSlashCommand,
  HttpSlashCommand,
  OnboardSlashCommand,
  ShareSlashCommand,
  ProjectGenSlashCommand,  // ← 新增这一行
];
```

#### 4. 编译和测试

```bash
# 在 continue 目录下
cd extensions/vscode

# 安装依赖（如果还没有）
npm install

# 编译
npm run compile

# 在 VSCode 中按 F5 启动调试
# 这会打开一个新的 VSCode 窗口，Continue 扩展已加载
```

#### 5. 使用命令

在新打开的 VSCode 窗口中：

1. 打开 Continue Chat 面板（Cmd/Ctrl + L）
2. 输入命令：
   ```
   /projectgen repo=bplustree dataset=CodeProjectEval model=gpt-4o
   ```
3. 观察生成进度

---

### 方案 B: 使用 Continue 的 /http 命令（快速验证）

如果你不想修改 Continue 源码，可以使用内置的 `/http` 命令作为临时方案。

#### 1. 在 Continue 配置中添加

打开 `~/.continue/config.json`，添加：

```json
{
  "slashCommands": [
    {
      "name": "projectgen",
      "description": "Generate project with ProjectGen",
      "prompt": "http",
      "params": {
        "url": "http://localhost:5000/api/chat/projectgen"
      }
    }
  ]
}
```

#### 2. 在服务器端添加兼容端点

在 `projectgen-server/main.py` 中添加：

```python
@app.post("/api/chat/projectgen")
async def chat_projectgen(request: dict):
    """
    兼容 Continue /http 命令的端点
    """
    input_text = request.get("input", "")
    
    # 解析输入
    # 格式: repo=bplustree dataset=CodeProjectEval
    import re
    repo_match = re.search(r'repo=(\S+)', input_text)
    dataset_match = re.search(r'dataset=(\S+)', input_text)
    
    if not repo_match:
        return {"response": "Error: Missing repo parameter"}
    
    repo_name = repo_match.group(1)
    dataset = dataset_match.group(1) if dataset_match else "CodeProjectEval"
    
    # 启动生成任务
    gen_request = GenerateRequest(
        dataset=dataset,
        repo_name=repo_name,
        requirement="Generated from chat",
        model="gpt-4o"
    )
    
    result = await generate_project(gen_request)
    
    return {
        "response": f"Started generation for {repo_name}. Project ID: {result.project_id}"
    }
```

#### 3. 使用

在 Continue Chat 中：
```
/projectgen repo=bplustree dataset=CodeProjectEval
```

**注意**：这种方式功能有限，无法显示实时进度。

---

## 🧪 测试

### 单元测试

```bash
# 测试服务器
cd projectgen-server
pytest tests/  # 需要先创建测试文件
```

### 集成测试

1. 启动服务器
2. 在 VSCode 中打开测试项目
3. 运行 `/projectgen` 命令
4. 验证：
   - 进度显示正确
   - 文件生成到正确位置
   - 错误处理正常

### 测试清单

- [ ] 服务器启动正常
- [ ] 健康检查返回正确
- [ ] 生成任务创建成功
- [ ] 状态查询正常
- [ ] WebSocket 连接正常
- [ ] SlashCommand 注册成功
- [ ] 命令执行无错误
- [ ] 进度显示正确
- [ ] 文件写入成功
- [ ] 错误处理正确

---

## 🐛 故障排除

### 问题 1: 服务器无法启动

**症状**: `python main.py` 报错

**解决**:
```bash
# 检查 Python 版本
python --version  # 应该 >= 3.9

# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 检查端口占用
lsof -i :5000
```

### 问题 2: Continue 无法识别命令

**症状**: 输入 `/projectgen` 没有反应

**解决**:
1. 确认已重新编译：`npm run compile`
2. 重启 VSCode 调试窗口
3. 检查 `index.ts` 中是否正确导入和注册
4. 查看 Continue 日志：`Continue: View Logs`

### 问题 3: CORS 错误

**症状**: 浏览器控制台显示 CORS 错误

**解决**:
在 `main.py` 中确认 CORS 配置：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或具体的 VSCode Webview 域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题 4: 无法读取 PRD 文件

**症状**: 错误信息 "Cannot read PRD file"

**解决**:
1. 确认文件路径正确
2. 检查文件权限
3. 使用绝对路径测试：
   ```typescript
   const prdPath = "/absolute/path/to/PRD.md";
   ```

---

## 📦 部署到生产环境

### Docker 部署

创建 `projectgen-server/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY main.py .
COPY ../src /app/src

# 暴露端口
EXPOSE 5000

# 启动服务
CMD ["python", "main.py"]
```

构建和运行：

```bash
# 构建镜像
docker build -t projectgen-server:latest .

# 运行容器
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your_key \
  projectgen-server:latest
```

### 发布 VSCode 扩展

1. **Fork Continue 仓库**
2. **修改扩展名称**（避免冲突）
   - 编辑 `extensions/vscode/package.json`
   - 修改 `name`, `displayName`, `publisher`
3. **打包扩展**
   ```bash
   cd extensions/vscode
   npm run package
   ```
4. **发布到 Marketplace**
   ```bash
   vsce publish
   ```

---

## 📚 下一步

### 功能增强

1. **WebSocket 实时更新**
   - 在 GUI 中实现 WebSocket 客户端
   - 替代当前的轮询机制

2. **记忆查看功能**
   - 实现 ContextProvider
   - 显示各阶段的记忆内容

3. **配置管理**
   - 支持用户自定义服务器地址
   - 模型选择界面

4. **错误恢复**
   - 任务失败后重试
   - 断点续传

### 性能优化

1. 使用 Redis 存储任务状态
2. 实现任务队列
3. 添加缓存机制
4. 优化大文件处理

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目遵循 Apache 2.0 许可证。
