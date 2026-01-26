# ProjectGen - 类 Continue 插件使用指南

## 架构说明

ProjectGen 现在是一个完全类似 Continue 的 VSCode 扩展：

- ✅ **侧边栏集成**: 在 VSCode 左侧活动栏有独立图标
- ✅ **聊天界面**: 复用 Continue 的完整 GUI 和样式系统  
- ✅ **无账号功能**: 精简版，专注于代码生成
- ✅ **仓库级代码生成**: 核心功能

## 文件结构

```
projectgen-extension/
├── src/
│   ├── extension.ts                      # 扩展入口
│   ├── ProjectGenWebviewViewProvider.ts  # 侧边栏视图提供者
│   └── panel.ts                          # (旧文件，可删除)
├── gui/                                  # 符号链接到 continue/gui
├── media/
│   └── icon.svg                          # 侧边栏图标
├── package.json                          # 扩展配置
└── tsconfig.json                         # TypeScript配置
```

## 启动步骤

### 1. 启动后端服务器

```bash
cd /Users/lv.sany/Documents/Uni_workplace/sci/AI4SE/codegen-on-continue
./run.sh
```

服务器将在 http://localhost:5002 运行

### 2. 启动扩展（开发模式）

```bash
cd projectgen-extension
code .
```

在新打开的 VSCode 窗口中按 **F5**

### 3. 使用扩展

在扩展开发窗口中（标题显示 `[Extension Development Host]`）：

1. 点击左侧活动栏的 **P** 图标（ProjectGen）
2. 侧边栏会打开，显示类似 Continue 的聊天界面
3. 在聊天框输入代码生成请求

或使用快捷键：
- **Cmd+Shift+P** (macOS) 打开聊天窗口

## 开发模式说明

### 使用 Continue GUI（开发模式）

扩展会自动连接到 Continue 的 Vite 开发服务器：

```bash
# 在 continue/gui 目录启动开发服务器
cd continue/gui
npm run dev
```

GUI 将在 http://localhost:5173 运行，支持热重载。

### 生产模式

生产模式需要构建 Continue GUI：

```bash
cd continue/gui
npm run build
```

构建产物在 `continue/gui/assets/`，扩展会自动加载。

## 与原版 Continue 的区别

| 功能 | Continue | ProjectGen |
|------|----------|------------|
| 侧边栏图标 | Continue 图标 | P 图标 |
| 账号登录 | ✅ | ❌ |
| 多模型支持 | ✅ | ❌ |
| 代码补全 | ✅ | ❌ |
| 代码编辑 | ✅ | ❌ |
| 仓库生成 | ❌ | ✅ |
| 聊天界面 | ✅ | ✅ (复用) |

## 后续开发

如果需要自定义 GUI，修改 `continue/gui/src/` 下的文件即可：

- `pages/gui/Chat.tsx` - 主聊天界面
- `components/` - UI 组件
- `redux/` - 状态管理

所有修改会在开发模式下自动热重载。

## 故障排查

### 侧边栏不显示

检查 package.json 中的 `viewsContainers` 和 `views` 配置。

### GUI 加载失败

1. 确保 Continue GUI 开发服务器在运行（`npm run dev`）
2. 检查 Console 输出的错误信息
3. 验证符号链接：`ls -la gui`

### 样式不正确

确保 `window.ide = "vscode"` 已在 HTML 中设置，Continue GUI 会据此加载 VSCode 主题。
