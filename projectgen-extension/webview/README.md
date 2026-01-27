# ProjectGen 简化前端

这是一个不依赖 Continue 的简化版 VS Code 扩展前端。

## 特性

- ✅ **纯原生实现**：使用原生 HTML/CSS/JavaScript，无需 React 或其他框架
- ✅ **轻量级**：无需构建步骤，直接加载 HTML 文件
- ✅ **自包含**：所有样式和脚本都在一个文件中
- ✅ **美观界面**：使用 VS Code 主题变量，完美融入编辑器
- ✅ **实时交互**：支持实时消息发送和接收

## 界面功能

### 主要功能

1. **聊天界面**
   - 用户消息（蓝色气泡，右对齐）
   - 助手消息（灰色气泡，左对齐）
   - 错误消息（红色边框）
   - 信息提示（蓝色边框）

2. **输入区域**
   - 自动调整高度的文本框
   - 支持 Ctrl/Cmd + Enter 快捷键发送
   - 发送按钮

3. **快捷操作**
   - 清空对话
   - 新会话

4. **欢迎界面**
   - 建议的项目模板
   - 一键填充需求

### 消息类型

扩展支持以下消息类型：

- `result`: 成功结果（绿色 ✅）
- `error`: 错误消息（红色 ❌）
- `info`: 信息提示（蓝色 ℹ️）
- `progress`: 进度更新（黄色 ⏳）

## 文件结构

```
webview/
├── index.html          # 主界面文件（包含 HTML/CSS/JS）
└── README.md          # 本文档
```

## 与后端通信

### 前端发送消息

```javascript
vscode.postMessage({
    type: 'generate',
    message: '用户输入的需求描述'
});
```

### 后端返回消息

```javascript
{
    type: 'result' | 'error' | 'info' | 'progress',
    content: '消息内容'
}
```

## 使用说明

### 开发模式

1. 编译扩展：
```bash
cd projectgen-extension
npm install
npm run compile
```

2. 按 F5 启动调试

3. 在扩展开发主机中打开侧边栏的 ProjectGen 视图

### 修改界面

直接编辑 `webview/index.html` 文件，保存后重新加载窗口即可看到效果。

### 自定义样式

所有样式使用 VS Code CSS 变量：

- `--vscode-editor-background`: 编辑器背景色
- `--vscode-editor-foreground`: 编辑器前景色
- `--vscode-button-background`: 按钮背景色
- `--vscode-input-background`: 输入框背景色
- 等等...

这确保了界面会自动适配用户选择的主题。

## 优势对比

### 相比 Continue 集成方案

| 方面 | 简化前端 | Continue 集成 |
|------|---------|---------------|
| 依赖 | 无外部依赖 | 依赖 Continue 扩展 |
| 构建 | 无需构建 | 需要 Vite 构建 |
| 大小 | < 20KB | > 1MB |
| 启动 | 即时加载 | 需要加载 React |
| 维护 | 简单直接 | 需要同步 Continue 更新 |
| 自定义 | 完全控制 | 受限于 Continue API |

## 扩展功能建议

可以考虑添加以下功能：

1. **markdown 渲染**：使用 marked.js 渲染 markdown
2. **代码高亮**：使用 highlight.js 高亮代码块
3. **历史记录**：保存对话历史到本地
4. **导出功能**：导出对话为文件
5. **进度条**：显示生成进度
6. **文件预览**：预览生成的文件

## 故障排除

### 界面不显示

检查 `webview/index.html` 文件是否存在，路径是否正确。

### 无法连接后端

确保 ProjectGen 服务器在 `http://localhost:5002` 运行。

### CSP 错误

如果看到内容安全策略错误，需要在 HTML 的 `<meta>` 标签中添加相应的允许规则。
