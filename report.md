ProjectGen 插件实现与协同机制汇报文档

1. 系统组成

ProjectGen 由三部分组成：VS Code
插件（projectgen-extension）、服务端（projectgen-server
）、生成引擎（./src）。
插件负责界面与交互。
服务端负责任务管理与 API。
./src 负责多代理代码生成与评测。

2. 插件实现原理（projectgen-extension）

插件入口是 src/extension.ts。
插件在 Activity Bar 注册 projectgen.chatView Webview 视图。
Webview 前端是 React + Redux，代码在 gui/src，构建产物在 dist/gui/assets。
Webview 通过 acquireVsCodeApi().postMessage() 向扩展宿主发送消息。
扩展宿主通过 onDidReceiveMessage 处理
generateFromRepo、stopGeneration、openFile、
modelConfigChanged 等消息。
扩展宿主通过 HTTP 调用服务端接口。
扩展宿主轮询任务状态与文件列表并回推给 Webview。
Webview 根据 progress/newFile/files/error/info 消息更新界面状态。
文件打开操作在宿主侧做路径归一化和目录边界校验，阻止越界访问。

3. 插件与服务端通信

生成任务创建接口是 POST /api/projects/generate。
任务状态接口是 GET /api/projects/{project_id}/status。
文件列表接口是 GET /api/projects/{project_id}/files。
取消任务接口是 POST /api/projects/{project_id}/cancel。
插件默认服务地址是 projectgen.serverUrl，默认值为 http://localhost:5002。
插件只做编排与展示，不执行生成算法。

4. 服务端与 ./src 的协同方式

服务端入口是 projectgen-server/main.py。
服务端启动时将项目 src 目录加入 sys.path。
服务端在子进程中执行 from workflow import build_graph 并调用
graph.invoke(initial_state)。
src/workflow.py 组织 architecture、skeleton、code 及对应 judge agent
的流程图。
各 agent 在 src/agents/* 中实现。
中间产物写入输出目录 tmp_files，包括
architecture_*、skeleton_*、generated_code_*.jsonl。
服务端将这些产物暴露给插件读取。

5. 服务端如何知道任务状态

服务端使用内存字典 tasks 保存任务运行态。
每个任务创建后记录 project_id、status、worker_process、repo_dir、status_file
 等字段。
任务在子进程执行，结束时将最终状态写入
tmp_files/.projectgen_task_status.json。
状态查询接口会调用 sync_task_with_worker() 同步子进程结果。
如果子进程仍在运行，服务端通过扫描 tmp_files 文件名推断当前阶段与迭代次数。
阶段与迭代通过 progress_monitor.py 计算为进度百分比。
取消任务时服务端终止子进程并将任务状态设为 cancelled。

6. “状态在内存” 的含义

tasks 在服务端进程内存中。
服务端重启后 tasks 会清空。
重启后旧 project_id 通常无法继续查询。
这表示任务元数据丢失，不表示磁盘文件一定丢失。
已写到磁盘的生成代码通常仍在 projectgen_outputs/...。
如果重启发生在生成中，可能只保留部分已生成文件。

7. 端到端执行链路

用户在插件输入 /projectgen repo=<path>。
Webview 将命令发送给扩展宿主。
扩展宿主调用服务端创建任务并拿到 project_id。
扩展宿主轮询状态与文件接口。
服务端驱动 ./src 工作流执行生成和评测。
服务端返回阶段进度与文件产物。
插件实时展示进度并支持点击打开生成文件。