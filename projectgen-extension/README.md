# ProjectGen - 简化版 VS Code 扩展

## 简介

ProjectGen 是一个**轻量级的 AI 代码生成扩展**，完全不依赖 Continue。

特点：
- ✅ **纯原生实现**：使用原生 HTML/CSS/JavaScript
- ✅ **无需构建**：直接加载，无需 React/Vite
- ✅ **侧边栏集成**：在 VS Code 左侧活动栏有独立图标
- ✅ **简洁聊天界面**：美观的对话式交互
- ✅ **仓库级代码生成**：支持完整项目生成

## 架构说明

```
projectgen-extension/
├── src/
│   ├── extension.ts                      # 扩展入口
│   └── ProjectGenWebviewViewProvider.ts  # 侧边栏视图提供者
├── webview/
│   ├── index.html                        # 聊天界面（自包含，含CSS/JS）
│   └── README.md                         # 前端文档
├── media/
│   └── icon.svg                          # 侧边栏图标
├── package.json                          # 扩展配置
└── tsconfig.json                         # TypeScript配置
```

## 启动步骤

### 1. 启动后端服务器

```bash
cd /path/to/codegen-on-continue
./run.sh
```

服务器将在 http://localhost:5002 运行

### 2. 编译扩展

```bash
cd projectgen-extension
npm install
npm run compile
```

### 3. 启动扩展（开发模式）

在 VS Code 中：
1. 打开 `projectgen-extension` 文件夹
2. 按 **F5** 启动调试
3. 会打开一个新的 VS Code 窗口（扩展开发主机）

### 4. 使用扩展

在扩展开发窗口中：

1. 点击左侧活动栏的 **ProjectGen** 图标
2. 侧边栏会打开，显示聊天界面
3. 输入项目需求，点击"发送"按钮

或使用快捷键：
- **Cmd+Shift+P** (macOS) / **Ctrl+Shift+P** (Windows/Linux)
- 输入 "ProjectGen: Focus Chat"

## 使用示例

### 示例 1: 生成 TODO 应用

在聊天框输入：
```
生成一个简单的 TODO 应用，使用 Python Flask 后端和 HTML 前端
```

### 示例 2: 生成 API 项目

在聊天框输入：
```
创建一个用户管理 RESTful API，包含注册、登录、用户列表功能
```

扩展会：
1. 将需求发送到后端服务器
2. 显示进度信息
3. 生成完成后显示结果

## 界面功能

### 聊天界面

- **用户消息**：蓝色背景，右对齐
- **助手消息**：灰色背景，左对齐  
- **错误消息**：红色边框
- **进度提示**：蓝色边框

### 快捷操作

- **清空对话**：清除所有聊天记录
- **新会话**：开始新的对话会话

### 预设模板

点击建议的项目模板可快速填充需求：
- 📝 TODO 应用
- 🌐 RESTful API
- ⚛️ React 前端项目

## 技术架构

### 前端（webview/index.html）

- 纯 HTML/CSS/JavaScript 实现
- 使用 VS Code CSS 变量自动适配主题
- 无需构建步骤，即时加载

### 后端通信

扩展通过 HTTP POST 与 ProjectGen 服务器通信：

```typescript
POST http://localhost:5002/api/projects/generate
{
    "requirement": "用户输入的需求",
    "workspace_root": "/当前工作区路径"
}
```

服务器返回：
```json
{
    "output_dir": "/生成的项目路径",
    "message": "成功消息",
    "error": "错误消息（如有）"
}
```

## 自定义界面

直接编辑 `webview/index.html` 即可自定义界面。

### 修改样式

所有样式都使用 VS Code 主题变量：

```css
background: var(--vscode-editor-background);
color: var(--vscode-editor-foreground);
```

### 添加功能

在 `<script>` 标签中添加 JavaScript 代码：

```javascript
// 添加新的消息处理
window.addEventListener('message', event => {
    const message = event.data;
    // 处理自定义消息类型
});
```

## 对比 Continue 集成方案

| 方面 | 简化版 | Continue 集成 |
|------|--------|---------------|
| **依赖** | 无外部依赖 | 依赖 Continue 扩展 |
| **构建** | 无需构建 | 需要 Vite + React |
| **文件大小** | < 20KB | > 1MB |
| **启动速度** | 即时 | 需加载 React |
| **维护成本** | 低 | 需同步 Continue 更新 |
| **自定义性** | 完全控制 | 受限于 Continue API |
| **学习曲线** | HTML/CSS/JS | React + TypeScript |

## 故障排查

### 界面不显示

- 检查 `webview/index.html` 是否存在
- 查看 VS Code 开发者工具（Help > Toggle Developer Tools）
- 检查控制台错误信息

### 无法连接后端

- 确保后端服务器在运行：`curl http://localhost:5002`
- 检查防火墙设置
- 查看后端日志文件

### 编译错误

```bash
# 清理并重新安装依赖
rm -rf node_modules out
npm install
npm run compile
```

## 扩展功能建议

可以考虑添加：

1. **Markdown 渲染**：渲染富文本消息
2. **代码高亮**：语法高亮代码块
3. **历史记录**：保存对话历史
4. **导出功能**：导出对话为文件
5. **进度条**：显示详细的生成进度
6. **文件预览**：预览生成的文件内容

确保 `window.ide = "vscode"` 已在 HTML 中设置，Continue GUI 会据此加载 VSCode 主题。
