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
