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
