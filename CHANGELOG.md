# Changelog


## 2026-03-18 18:00

### Extension

- 将命令入口统一为路径模式：`/projectgen repo=<路径>`。
- 移除旧的 `dataset + repo_name` 自动查找交互逻辑。
- 支持相对路径输入，前端发送 `repo_path + workspace_root` 给后端解析。
- 修正空态示例路径，改为当前仓库真实可用路径（如 `./datasets/CodeProjectEval/bplustree`）。
- 错误提示从泛化文案升级为结构化信息展示（状态码 + 错误码 + 消息）。

### Server

- `POST /api/projects/generate` 改为以 `repo_path` 为核心输入。
- 后端统一解析相对路径（基于 `workspace_root`）。
- 输出目录统一使用 `PROJECTGEN_OUTPUT_DIR`（默认 `projectgen_outputs`）。
- 取消任务为进程级终止（子进程 terminate）。
- 统一异常返回格式，新增 `error_code` 与中文 `message`。
- 取消鉴权逻辑，当前接口不要求 token。

### Security and Robustness

- 去除聊天消息的 HTML 注入渲染，改为安全文本渲染。
- `openFile` 增加路径边界校验，阻止路径穿越访问。

### Scripts and Runtime

- `run.sh` 停止服务器流程调整为单一方式：发送 `INT` 并等待退出。
- `run.sh` 保留端口注入与服务存活检查逻辑。

### Docs

- 根目录 `README.md` 完整重写为当前可运行版本文档。
- 增加命令格式、路径规则、错误码、常见问题与构建说明。



## 2026-03-19

### Troubleshooting and Findings

- 排查 `/projectgen repo=./datasets/CodeProjectEval/bplustree` 失败问题，确认根因并非路径解析，而是模型供应商返回 `403 FORBIDDEN`（账户余额不足）。
- 明确 `status=running` 仅表示任务已启动，不代表生成成功；任务可能在后续阶段失败。
- 对比验证 `CodeProjectEval/bplustree` 与 `DevBench/chakin`：两者均可创建任务，均可能在后续因同一模型额度问题失败。

### Extension

- 改进请求失败兜底错误展示：避免 `请求失败:` 后为空白。
- 新增错误消息标准化逻辑（`normalizeErrorMessage`），在非 `Error` 对象场景下也能显示可读信息。
- 调整配置提示触发条件：仅在连接/地址/路径相关错误时显示 `projectgen.serverUrl` 与 `repo` 路径检查提示，降低误导性。

### Extension UI and Interaction

- 重构前端消息渲染：`/projectgen` 执行后仅保留单一会话卡片 `ProjectGen [path]`，不再向外部消息列表追加 `error/info/progress` 气泡。
- 所有反馈（进度、状态、错误）统一内聚到会话卡片内部展示，错误以紧凑内联错误态呈现。
- 修复命令兜底流程：当 `/projectgen` 命令格式不完整时，仍创建同一会话卡片并在卡片内显示错误信息。
- 调整生成状态机：`setError` 时结束 `isGenerating`，避免异常后 UI 长时间停留在“生成中”状态。
- 修复阶段假阳性：失败场景下不再仅按 `currentStage` 自动将前置阶段标记为完成；仅在有实际文件产出时标记 `✓`，失败阶段标记 `✕`。
- UI 配色改造：提升反馈区和错误信息可读性，统一为高对比度语义色变量驱动。
- 按当前产品要求裁剪主题：移除暗色/高对比模式专用样式分支，保留亮色模式实现与配色。

### Docs

- 同步文档口径：新增模型供应商 `403`（余额不足）场景说明，避免误判为路径问题。



## 2026-04-05 ~ 2026-04-06

### Feature: Continue-Style UI Migration (完整迁移)

#### 模型选择系统
- ✅ **多 Provider 支持**: OpenAI, Anthropic, DeepSeek, Ollama, OpenAI-Compatible
- ✅ **动态配置表单**: `AddModelForm.tsx` 根据 Provider 动态显示必填字段（API Key / Base URL）
- ✅ **PNG 图标系统**: 从 Continue 复制 7 个 Provider logo（`gui/public/logos/*.png`）
- ✅ **Redux 状态管理**: `modelConfigSlice` + localStorage 持久化存储用户配置
- ✅ **紧凑模式选择器**: 工具栏内嵌 `ModelSelector`，支持快速切换模型
- ✅ **后端环境变量注入**: `main.py` 根据 Provider 动态设置 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 等

#### 聊天历史与会话管理
- ✅ **统一时间线设计**: 合并 `ChatHistory` + `GenerationCard`，消除消息重复展示
- ✅ **会话标签栏**: `SessionTabs` 显示最近 5 个会话，支持切换/删除
- ✅ **历史列表面板**: 点击 `History` 按钮展开浮动面板，支持：
  - 搜索框实时过滤会话标题（模糊匹配）
  - 按日期分组展示（Today / Yesterday / 具体日期）
  - 显示每个会话的消息数量和最后更新时间
  - 点击会话行快速切换
- ✅ **localStorage 持久化**: 会话数据自动保存到 `projectgen_chat_history`，刷新后恢复
- ✅ **Clear 按钮修复**: 清空当前会话消息 + 输入框内容 + 生成状态

#### 生成进度统一
- ✅ **消息类型扩展**: 新增 `generation` 类型，携带 `metadata` (repo, stage, progress, files, error)
- ✅ **GenerationCard 组件**: 内嵌式三阶段卡片（Architecture → Skeleton → Code）
  - 支持展开/折叠文件列表
  - 实时进度条更新
  - 完成/错误状态显示
  - 文件点击在编辑器打开
- ✅ **无重复展示**: 移除独立的 `GenerationSession` 渲染，进度卡片直接嵌入时间线

#### UI 组件库与样式
- ✅ **Tailwind CSS 集成**: 配置 `tailwind.config.cjs` + PostCSS
- ✅ **VS Code 主题变量**: `theme.ts` 映射 `--vscode-*` 变量
- ✅ **通用组件**: Button, Listbox, Input, Divider, Transition
- ✅ **Continue 风格输入框**: `GradientBorder` + 彩虹边框动画（生成时激活）
- ✅ **InputToolbar 布局**: 左侧模型选择器，右侧操作按钮（Stop / Clear / Send）
- ✅ **去表情符号化**: 移除所有 emoji 文案（保留 `⏎ / ↻ / ■` 符号按钮）

### Code Architecture

#### 新增文件
- `gui/src/components/ui/` - Button, Listbox, Input, Divider, Transition
- `gui/src/components/ModelSelector.tsx` - 模型选择器（紧凑/完整模式）
- `gui/src/components/modelSelection/ModelSelectionListbox.tsx` - Provider/Model 下拉列表
- `gui/src/components/mainInput/ContinueStyleInput.tsx` - Continue 风格样式组件
- `gui/src/components/chat/ChatHistory.tsx` - 统一时间线渲染
- `gui/src/components/chat/SessionTabs.tsx` - 会话标签栏 + 历史面板
- `gui/src/components/chat/GenerationCard.tsx` - 生成阶段卡片
- `gui/src/configs/providers.ts` - 5 个 Provider 配置（含 PNG 图标路径）
- `gui/src/configs/models.ts` - 14 个模型定义
- `gui/src/redux/slices/modelConfigSlice.ts` - 模型配置状态
- `gui/src/redux/slices/chatHistorySlice.ts` - 聊天历史状态
- `gui/src/forms/AddModelForm.tsx` - 动态模型配置表单
- `gui/src/styles/theme.ts` - VS Code 主题变量映射
- `gui/src/util/cn.ts` - Tailwind class 合并工具
- `gui/tailwind.config.cjs` - Tailwind 配置
- `gui/postcss.config.cjs` - PostCSS 配置
- `gui/public/logos/*.png` - 7 个 Provider 图标

#### 修改文件
- `gui/src/App.tsx` - 重构主界面布局（SessionTabs + ChatHistory + Continue 风格输入）
- `gui/src/redux/store.ts` - 新增 `modelConfig` 和 `chatHistory` reducers
- `gui/src/components/mainInput/SimpleInput.tsx` - 改为 `forwardRef` + 暴露 `submit()` / `clear()` 方法
- `projectgen-server/main.py` - 新增 `provider` / `api_key` / `api_base` 参数，动态设置环境变量
- `src/ProjectGenWebviewViewProvider.ts` - 新增 `modelConfigChanged` 消息处理

### Breaking Changes

- **消息渲染逻辑变更**: 不再支持独立的 `GenerationSession` 组件，所有内容统一在 `ChatHistory` 时间线中渲染
- **模型配置格式**: 从硬编码 `"gpt-4o"` 改为结构化 `{ provider, model, title, apiKey?, apiBase? }`
- **localStorage Key**: 新增 `projectgen_model_configs` 和 `projectgen_chat_history`

### Performance

- **搜索优化**: 历史搜索使用 `useMemo` 缓存过滤结果，避免每次输入都重新计算
- **分组计算**: `groupedSessions` 仅在 `filteredSessions` 变化时重新分组
- **延迟写入**: 生成进度更新时不保存 localStorage，仅完成/错误时写入

### Bundle Size

- **Before**: ~405 KB (gzip: ~133 KB)
- **After**: ~416 KB (gzip: ~136 KB)
- **增量**: +11 KB (+3 KB gzipped) - 主要来自 Tailwind CSS 和新增组件

### User Experience

#### 改进前
```
[ModelSelector 独立在顶部]
[InputBox]
[Toolbar: Stop/Clear]
[ChatHistory: User/Assistant 消息]
[GenerationSession: 进度卡片] ← 内容重复！
```

#### 改进后
```
[SessionTabs: Chat1 | Chat2 | History▾ | New]
  └─ [HistoryPanel: 搜索 + 按日期分组的会话列表]
[ChatHistory 统一时间线]
  ├─ User: /projectgen repo=...
  └─ GenerationCard (内嵌)
      ├─ Architecture Design (3 files)
      ├─ Code Skeleton [进度条 45%]
      └─ Code Generation (pending)
[GradientBorder 输入框]
  [Toolbar: ModelSelector | ⏎ Enter | ■ Stop | ↻ Clear | ⏎ Send]
```

### Migration Notes

#### 对于扩展使用者
1. **首次打开**: 需要在模型选择器中配置 Provider 和 API Key
2. **会话迁移**: 旧版本的生成记录不会自动迁移到新的聊天历史
3. **清除数据**: 可在浏览器开发者工具 → Application → Local Storage 中删除 `projectgen_*` keys

#### 对于开发者
1. **构建要求**: 新增依赖 `tailwindcss`, `clsx`, `tailwind-merge`, `react-hook-form`
2. **主题变量**: 所有样式使用 `var(--vscode-*)` 变量，自动适配 VS Code 主题
3. **Provider 扩展**: 在 `gui/src/configs/providers.ts` 中添加新 Provider 配置
4. **图标添加**: 将 Provider logo (PNG) 放入 `gui/public/logos/` 目录

### Testing Checklist

- [x] 模型选择器显示正确的 Provider 和图标
- [x] 配置表单根据 Provider 动态显示字段
- [x] 历史搜索实时过滤会话标题
- [x] 历史面板按日期正确分组
- [x] 切换会话时正确加载历史消息
- [x] Clear 按钮清空当前会话和输入框
- [x] 生成进度卡片实时更新
- [x] 文件点击在编辑器中打开
- [x] localStorage 持久化和恢复
- [x] 多个 Provider 的 API Key 正确传递到后端

### 2026-04-06 Incremental Update: 历史消息编辑重提交流程

- 新增 **同会话历史消息重提交流程**：单击历史中的用户消息可直接进入编辑态，修改后点击“重新生成”即可在原会话继续。
- 复用 Continue 的核心交互思想：**按历史索引回溯并截断后续消息，再基于编辑后的输入重新发起请求**（对应 Continue `submitEditorAndInitAtIndex` / resubmit 机制）。
- 前端 `ChatHistory` 新增内联编辑器（支持 Enter 提交、Shift+Enter 换行、Esc 取消），并在生成中禁用编辑，避免状态冲突。
- Redux `chatHistorySlice` 新增 `editUserMessageAndTruncate`：更新目标用户消息、截断其后的 assistant/generation 消息、同步会话标题与本地持久化。
- `App.tsx` 新增重提交流程：编辑后会复用现有命令解析与生成链路（`/projectgen repo=...`），无需新建会话。
