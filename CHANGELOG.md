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