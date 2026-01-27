# ProjectGen React GUI

ProjectGen的前端已经升级到React，使用了与Continue类似的技术栈。

## 技术栈

- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Redux Toolkit** - 状态管理
- **Styled Components** - CSS-in-JS
- **Vite** - 构建工具

## 从Continue复用的组件

1. **样式常量** (`src/components/index.ts`)
   - 从Continue复制的VS Code主题颜色变量

2. **输入框组件** (`src/components/mainInput/`)
   - `SimpleInput.tsx` - 简化的输入框（参考TipTapEditor）
   - `StyledComponents.tsx` - 样式化组件

3. **聊天组件** (`src/components/chat/`)
   - `ChatMessage.tsx` - 消息气泡组件
   - `ProgressDisplay.tsx` - 进度显示组件
   - `FileList.tsx` - 文件列表组件

## 项目结构

```
gui/
├── src/
│   ├── components/       # UI组件
│   │   ├── chat/        # 聊天相关组件
│   │   └── mainInput/   # 输入框相关组件
│   ├── context/         # React Context
│   ├── redux/           # Redux状态管理
│   │   └── slices/      # Redux slices
│   ├── util/            # 工具函数
│   ├── App.tsx          # 主应用组件
│   ├── main.tsx         # 入口文件
│   └── index.css        # 全局样式
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 开发

```bash
# 安装依赖
cd gui
npm install

# 开发模式
npm run dev

# 构建
npm run build
```

## 构建产物

构建后的文件会输出到 `../dist/gui/`：
- `index.html`
- `assets/index.js`
- `assets/index.css`

## 与扩展集成

扩展的 `ProjectGenWebviewViewProvider.ts` 会加载构建后的React应用：

```typescript
private _getHtmlForWebview(webview: vscode.Webview) {
    const scriptUri = webview.asWebviewUri(
        vscode.Uri.joinPath(this._extensionUri, 'dist', 'gui', 'assets', 'index.js')
    );
    const styleUri = webview.asWebviewUri(
        vscode.Uri.joinPath(this._extensionUri, 'dist', 'gui', 'assets', 'index.css')
    );
    // ...
}
```

## 功能特性

### 1. Redux状态管理
- 生成状态跟踪
- 进度更新
- 文件列表管理

### 2. 实时更新
- 通过VS Code webview消息API与扩展通信
- 实时显示生成进度
- 增量显示文件

### 3. UI/UX
- 参考Continue的现代UI设计
- 支持Enter发送、Shift+Enter换行
- 文件点击打开编辑器
- 区分临时文件和项目文件

### 4. 类型安全
- 完整的TypeScript类型定义
- Redux Toolkit类型推断
- VS Code API类型支持

## 测试

1. 按 F5 启动扩展调试
2. 在扩展开发主机中打开ProjectGen视图
3. 输入命令如 `/projectgen repo=bplustree`
4. 观察实时进度和文件显示

## 下一步优化

可以继续从Continue复用更多组件：
- TipTap富文本编辑器（更强大的输入体验）
- @mention功能（上下文引用）
- 代码高亮显示
- Markdown渲染
