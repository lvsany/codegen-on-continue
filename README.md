# ProjectGen (Extension + Server)

这是当前可运行版本的 ProjectGen 文档，覆盖 VS Code 插件与本地后端服务的实际行为。

## 1. 当前能力

- 在 VS Code 侧边栏运行 ProjectGen。
- 通过命令触发项目级生成。
- 实时轮询阶段进度并增量展示文件。
- 支持停止任务、查看生成文件并在编辑器中打开。
- 支持仓库路径输入（绝对路径，或基于 workspace 的相对路径）。

## 2. 命令格式

唯一有效命令：

```text
/projectgen repo=<路径>
```

示例：

```text
/projectgen repo=./datasets/CodeProjectEval/bplustree
/projectgen repo=./datasets/CodeProjectEval/flask
/projectgen repo=/absolute/path/to/repo
```

说明：

- `repo` 参数必须是仓库目录路径。
- 相对路径由后端基于 `workspace_root` 统一解析。
- 旧的 `dataset + repo_name` 自动搜索逻辑已移除。

## 3. 启动方式

### 3.1 启动后端

```bash
cd projectgen-server
pip install -r requirements.txt
python main.py
```

默认地址：`http://localhost:5002`

### 3.2 启动扩展

```bash
cd projectgen-extension
npm install
npm run compile
```

在 VS Code 打开 `projectgen-extension`，按 `F5` 启动扩展开发主机。

## 4. 配置项

扩展配置：

- `projectgen.serverUrl`：后端服务地址，默认 `http://localhost:5002`

说明：

- 当前版本不需要任何鉴权配置。

## 5. API 与错误处理

核心接口：

- `GET /api/health`
- `POST /api/projects/generate`
- `GET /api/projects/{project_id}/status`
- `POST /api/projects/{project_id}/cancel`
- `GET /api/projects/{project_id}/files`

### 5.1 统一错误返回

后端错误响应格式：

```json
{
  "detail": {
    "status": 404,
    "error_code": "REPO_NOT_FOUND",
    "message": "仓库路径不存在或不是目录",
    "detail": {
      "resolved_repo_path": "/abs/path"
    }
  }
}
```

常见错误码：

- `INVALID_REPO_PATH`：路径为空或非法。
- `REPO_NOT_FOUND`：仓库目录不存在。
- `REPO_CONFIG_MISSING`：缺少 `config.json`。
- `REPO_CONFIG_INVALID_JSON`：`config.json` 不是有效 JSON。
- `PROJECT_NOT_FOUND`：任务 ID 不存在。
- `PROJECT_NOT_CANCELLABLE`：任务状态不可取消。

前端会优先显示：`HTTP 状态 + error_code + message`。

## 6. 输出目录

后端输出目录由 `PROJECTGEN_OUTPUT_DIR` 决定，默认：

```text
<repo_root>/projectgen_outputs/<model>/<repo_name>/
```

## 7. 安全与稳定性（当前状态）

- 已移除聊天消息 HTML 注入渲染，默认纯文本显示。
- 文件打开使用输出目录边界校验，阻止路径穿越。
- 停止任务为进程级终止（后端子进程）。
- `run.sh` 停服逻辑为单一方式：发送 `INT` 并等待退出。

## 8. 常见问题

### 8.1 404: REPO_NOT_FOUND

请确认传入路径真实存在，例如：

```bash
find datasets -type d -name bplustree
```

本仓库中可用路径示例：

- `./datasets/CodeProjectEval/bplustree`

### 8.2 UI 示例路径未更新

如果源码已改但界面仍显示旧示例，重新构建 GUI：

```bash
cd projectgen-extension
npm run build:gui
```

## 9. 关键文件

- 插件入口: `projectgen-extension/src/extension.ts`
- Webview 通信: `projectgen-extension/src/ProjectGenWebviewViewProvider.ts`
- 前端界面: `projectgen-extension/gui/src/App.tsx`
- 后端服务: `projectgen-server/main.py`
- 启动脚本: `run.sh`
