# ProjectGen × Continue 实施指南（通俗易懂版）

**更新日期**: 2026年1月21日  
**适合人群**: 有基础 Python/TypeScript 知识的开发者  
**预计时间**: 2-3小时完成所有步骤

---

## 🎯 我们要做什么？

把你的 ProjectGen 代码(src/)套上 Continue 的聊天界面，让它更好用。

**效果**：
- 在 VSCode 聊天窗口输入：`/projectgen repo=bplustree`
- 自动读取配置、生成代码、显示进度
- 生成的代码直接出现在工作区

**不需要**：
- 改动 src/ 的任何代码
- 学习复杂的框架
- 写很多新代码（总共约500行）

---

## 📋 开始前的准备

### 1. 确认环境

```bash
# Python 版本
python --version  # 应该是 3.9+

# Node.js 版本
node --version  # 应该是 18.0+

# 测试 src/ 能不能跑
cd src
python main.py --dataset CodeProjectEval  # 确保没报错
```

### 2. 需要的工具

- VSCode (已安装)
- Terminal (终端)
- 文本编辑器 (VSCode 自带)

---

## 🚀 第一步：创建后台服务器（30分钟）

### 为什么需要这个？

你的 `src/workflow.py` 执行时会"卡住"，需要一个后台服务器来运行它。

### 1.1 创建目录和文件

```bash
# 进入项目根目录
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen

# 创建服务器目录
mkdir projectgen-server
cd projectgen-server
```

### 1.2 创建依赖文件

```bash
# 创建 requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
python-dotenv==1.0.0
EOF

# 安装依赖
pip install -r requirements.txt
```

等待安装完成（可能需要1-2分钟）。

### 1.3 创建配置文件

```bash
# 创建 .env 配置文件
cat > .env << 'EOF'
PROJECTGEN_DATASET_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/datasets
PROJECTGEN_OUTPUT_DIR=/Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/outputs
PORT=5000
EOF
```

**注意**：把路径改成你的实际路径！

### 1.4 创建服务器主文件 `main.py`

参考 [design.md](design.md) 中的"第一步"部分的完整代码，创建约150行的 `main.py`。

**核心功能**：
- 3个 API 接口：`/api/health`, `/api/projects/generate`, `/api/projects/{id}/status`, `/api/projects/{id}/files`
- 使用线程池后台执行 workflow
- 监控进度

### 1.5 创建进度监控器 `progress_monitor.py`

参考 [design.md](design.md) 中的"第二步"部分的完整代码，创建约50行的 `progress_monitor.py`。

**核心功能**：
- 检查 tmp_files/ 目录
- 判断当前阶段（architecture/skeleton/code）

### 1.6 测试服务器

```bash
# 启动服务器
python main.py
```

**成功的话会看到**：
```
🚀 ProjectGen Server starting...
📁 Dataset: /Users/.../datasets
📁 Output: /Users/.../outputs
🌐 Server: http://0.0.0.0:5000
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:5000
```

**在另一个终端测试**：
```bash
curl http://localhost:5000/api/health
# 应该返回: {"status":"healthy","active_tasks":0,"total_tasks":0}
```

✅ 第一步完成！

---

## 🎨 第二步：修改 Continue 代码（1小时）

### 为什么要改 Continue？

Continue 本来没有生成项目的功能，我们要加一个新命令。

### 2.1 找到 Continue 目录

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/continue
```

### 2.2 创建命令文件

```bash
cd core/commands/slash/built-in-legacy
touch projectgen.ts
```

**编辑 `projectgen.ts`**，参考 [design.md](design.md) 中"第三步"的完整代码（约300行）。

**核心功能**：
- 解析用户输入 (`/projectgen repo=bplustree`)
- 读取 PRD.md
- 调用服务器 API
- 轮询进度并显示
- 获取生成的文件并写入工作区

### 2.3 注册命令

**编辑 `continue/core/commands/slash/built-in-legacy/index.ts`**：

在文件**最顶部**（第1行后面）加一行：
```typescript
import ProjectGenSlashCommand from "./projectgen.js";
```

找到 `LegacyBuiltInSlashCommands` 数组，在里面加一个元素：
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

### 2.4 编译 Continue

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/new-projectgen/continue/extensions/vscode

# 第一次需要安装依赖
npm install

# 编译
npm run compile
```

**成功的话会看到**：
```
Compilation complete. Watching for file changes.
```

✅ 第二步完成！

---

## 🧪 第三步：测试完整流程（30分钟）

### 3.1 启动服务器

**打开终端1**：
```bash
cd projectgen-server
python main.py
```

保持这个终端运行。

### 3.2 启动 VSCode 调试

1. 在 VSCode 中打开 `continue` 文件夹
2. 按 `F5` 键（或点击"Run" → "Start Debugging"）
3. 会弹出一个新的 VSCode 窗口

### 3.3 在新窗口中测试

1. 在新窗口中，打开你的项目文件夹：
   ```
   File → Open Folder → 选择 new-projectgen
   ```

2. 按 `Cmd+L`（Mac）或 `Ctrl+L`（Windows）打开 Continue Chat

3. 输入命令：
   ```
   /projectgen repo=bplustree dataset=CodeProjectEval
   ```

4. 观察输出！

### 3.4 预期效果

你应该看到类似这样的输出：

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
└──────────────┘     └──────────────┘     └──────────────┘

⏳ Progress:

🏗️ Architecture Design
  - Iteration 1
[████░░░░░░░░░░░░░░░░] 20%

（... 继续显示进度 ...）

🎉 Generation Completed!

📝 Writing files to workspace...
  ✓ bplustree.py
  ✓ node.py
  ...

📁 Output directory: `CodeProjectEval_outputs/bplustree`
```

---

## 🐛 遇到问题？

### 问题1：服务器启动失败

**错误**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**:
```bash
cd projectgen-server
pip install -r requirements.txt
```

### 问题2：找不到 PRD.md

**错误**: `Cannot read PRD file`

**解决**:
1. 检查路径是否正确
2. 确认文件确实存在：
   ```bash
   ls datasets/CodeProjectEval/bplustree/PRD.md
   ```

### 问题3：Continue 没有显示命令

**解决**:
1. 确认编译成功：`npm run compile`
2. 重启 VSCode 调试窗口（关掉重新按 F5）
3. 查看 Continue 日志：按 `Cmd+Shift+P`，输入 "Continue: View Logs"

### 问题4：服务器连接失败

**错误**: `Cannot connect to server`

**解决**:
1. 确认服务器在运行：
   ```bash
   curl http://localhost:5000/api/health
   ```
2. 检查端口是否被占用：
   ```bash
   lsof -i :5000
   ```

### 问题5：编译报错

**错误**: TypeScript 编译错误

**解决**:
1. 确认 Node.js 版本：`node --version` (需要 18.0+)
2. 重新安装依赖：
   ```bash
   cd continue/extensions/vscode
   rm -rf node_modules
   npm install
   npm run compile
   ```

---

## ✅ 检查清单

完成后确认这些：

- [ ] 服务器能成功启动（端口5000）
- [ ] 健康检查返回正常（`curl http://localhost:5000/api/health`）
- [ ] Continue 编译成功
- [ ] VSCode 调试窗口能打开
- [ ] 能看到 `/projectgen` 命令
- [ ] 命令能成功读取 PRD.md
- [ ] 能看到进度显示
- [ ] 生成的文件出现在工作区

---

## 📊 总结

你做了什么？

1. **创建了一个轻量级服务器**（150行代码）
   - 接收请求
   - 调用 workflow
   - 返回结果

2. **创建了一个进度监控器**（50行代码）
   - 查看文件
   - 判断进度

3. **添加了一个 Continue 命令**（300行代码）
   - 读取配置
   - 调用服务器
   - 显示进度
   - 写入文件

**总共约500行新代码，src/ 完全不动！**

---

## 🎯 核心理念（重要！）

### Continue 只是"壳"

- Continue 提供：聊天界面、文件读写能力
- ProjectGen (src/) 是核心：所有生成逻辑都在这里
- 服务器是"中转站"：连接两者

### 数据流向

```
用户输入 → Continue 读取配置 → 服务器接收请求 
→ 服务器调用 workflow.py → agents 生成代码 
→ 保存到 tmp_files/ → 服务器返回结果 
→ Continue 写入工作区 → 完成！
```

### 为什么要这样？

1. ✅ **src/ 代码不需要改** - 保持原有逻辑
2. ✅ **利用 Continue 界面** - 美观易用
3. ✅ **松耦合** - 服务器、Continue、ProjectGen 可独立测试
4. ✅ **可扩展** - 以后可以加更多功能

---

## 🎉 完成了！

现在你可以：
- 在 VSCode 聊天窗口输入 `/projectgen repo=xxx` 生成项目
- 看到实时进度
- 生成的代码自动出现在工作区

需要帮助？查看 [PROBLEMS_SUMMARY.md](PROBLEMS_SUMMARY.md) 了解常见问题的解决方案。

---

## 📚 相关文档

- [design.md](design.md) - 完整的设计方案和代码
- [PROBLEMS_SUMMARY.md](PROBLEMS_SUMMARY.md) - 问题总结和解决方案
- [FINAL_DESIGN_PROPOSAL.md](FINAL_DESIGN_PROPOSAL.md) - 原始设计文档（已废弃）
