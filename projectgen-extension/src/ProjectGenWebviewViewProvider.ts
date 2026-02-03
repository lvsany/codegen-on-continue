import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';

interface ProjectGenResponse {
    error?: string;
    output_dir?: string;
    message?: string;
    status?: string;
    project_id?: string;
}

interface ProjectStatusResponse {
    project_id: string;
    status: string;
    current_stage: string;
    iteration: number;
    progress: number;
    message: string;
    error?: string;
}

interface GeneratedFile {
    path: string;
    content?: string;
}

interface FilesResponse {
    project_id: string;
    repo_name: string;
    files: GeneratedFile[];
    total_files: number;
    status: string;
}

// Helper function to make HTTP requests
function httpRequest(url: string, options: { method: string; headers?: Record<string, string>; body?: string }): Promise<{ ok: boolean; status: number; statusText: string; json: () => Promise<any>; text: () => Promise<string> }> {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const requestOptions: http.RequestOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port || 80,
            path: urlObj.pathname + urlObj.search,
            method: options.method,
            headers: options.headers || {}
        };

        const req = http.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    ok: res.statusCode ? res.statusCode >= 200 && res.statusCode < 300 : false,
                    status: res.statusCode || 0,
                    statusText: res.statusMessage || '',
                    json: async () => JSON.parse(data),
                    text: async () => data
                });
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        if (options.body) {
            req.write(options.body);
        }
        req.end();
    });
}

export class ProjectGenWebviewViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'projectgen.chatView';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this._extensionUri, 'dist')
            ]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            console.log('[ProjectGen] Received message from webview:', data.type, data);
            switch (data.type) {
                case 'generate':
                    await this.handleGenerate(data);
                    break;
                case 'generateFromRepo':
                    await this.handleGenerateFromRepo(data);
                    break;
                case 'openFile':
                    await this.handleOpenFile(data);
                    break;
                case 'newSession':
                    this.handleNewSession();
                    break;
                case 'stopGeneration':
                    this.handleStopGeneration();
                    break;
            }
        });
    }

    private _abortController: AbortController | null = null;
    private _currentProjectId: string | null = null;
    private _currentRepoName: string | null = null;  // 跟踪当前项目名称

    private async handleStopGeneration() {
        // 如果有正在进行的HTTP请求，取消它
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        
        // 如果有正在生成的项目，通知服务器取消
        if (this._currentProjectId) {
            try {
                await httpRequest(`http://localhost:5002/api/projects/${this._currentProjectId}/cancel`, {
                    method: 'POST'
                });
                this.postMessage({ type: 'info', content: '已请求停止生成任务' });
            } catch (error: any) {
                this.postMessage({ type: 'error', content: `停止任务失败: ${error.message}` });
            }
            this._currentProjectId = null;
        } else {
            this.postMessage({ type: 'info', content: '没有正在运行的生成任务' });
        }
    }

    private async handleGenerate(data: any) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            this.postMessage({ type: 'error', content: '请先打开一个工作区文件夹' });
            return;
        }

        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        const userMessage = data.message;

        try {
            // Send progress update
            this.postMessage({ type: 'info', content: '正在连接到 ProjectGen 服务器...' });

            // 对于自然语言需求，我们需要一个默认的repo或者让用户指定
            // 这里暂时使用一个示例repo，实际应该有个repo选择界面
            const response = await httpRequest('http://localhost:5002/api/projects/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: 'DevBench',
                    repo_name: 'readtime',  // 使用DevBench中实际存在的项目
                    requirement: userMessage,
                    model: 'gpt-4o'
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`服务器返回错误: ${response.status} ${response.statusText}\n${errorText}`);
            }

            const result = await response.json() as any;
            
            if (result.project_id) {
                // 记录当前项目 ID
                this._currentProjectId = result.project_id;
                
                // 服务器返回格式: {project_id, status, message}
                this.postMessage({ 
                    type: 'result', 
                    content: `✅ 项目生成任务已创建！\n\nProject ID: ${result.project_id}\nStatus: ${result.status}\n${result.message || ''}\n\n可以使用 project_id 查询生成进度。` 
                });
            } else {
                this.postMessage({ type: 'error', content: `生成失败: 服务器返回格式错误` });
            }
        } catch (error: any) {
            this.postMessage({ 
                type: 'error', 
                content: `连接失败: ${error.message}\n\n请确保 ProjectGen 服务器正在运行 (http://localhost:5002)` 
            });
        }
    }

    private async handleGenerateFromRepo(data: any) {
        console.log('[ProjectGen] handleGenerateFromRepo called with data:', data);
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            this.postMessage({ type: 'error', content: '请先打开一个工作区文件夹' });
            return;
        }

        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        const repo = data.repo;
        console.log('[ProjectGen] Processing repo:', repo);
        // 支持指定数据集，格式: dataset:repo 或 dataset/repo，如果不指定则自动搜索
        let dataset = '';  // 空字符串表示自动搜索
        let repoName = repo;
        
        // 解析 dataset:repo 或 dataset/repo 格式
        if (repo.includes(':')) {
            [dataset, repoName] = repo.split(':');
        } else if (repo.includes('/')) {
            [dataset, repoName] = repo.split('/');
        }
        // 如果没有分隔符，dataset 保持为空，服务器会自动搜索

        try {
            const displayText = dataset 
                ? `正在从 ${dataset}/${repoName} 生成项目...` 
                : `正在搜索并生成项目 ${repoName}...`;
            this.postMessage({ type: 'info', content: displayText });

            const response = await httpRequest('http://localhost:5002/api/projects/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: dataset,  // 空字符串表示自动搜索
                    repo_name: repoName,
                    requirement: `Generate project for ${repoName}`,
                    model: 'gpt-4o'
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`服务器返回错误: ${response.status} ${response.statusText}\n${errorText}`);
            }

            const result = await response.json() as any;
            
            if (result.project_id) {                // 记录当前项目 ID
                this._currentProjectId = result.project_id;
                this._currentRepoName = repoName;  // 记录repo名称
                                // 开始轮询进度
                this.pollProgress(result.project_id, repo);
            } else {
                this.postMessage({ type: 'error', content: `生成失败: 服务器返回格式错误` });
            }
        } catch (error: any) {
            this.postMessage({ 
                type: 'error', 
                content: `连接失败: ${error.message}\n\n请确保 ProjectGen 服务器正在运行 (http://localhost:5002)` 
            });
        }
    }

    private async pollProgress(projectId: string, repo: string) {
        let knownFiles = new Set<string>();
        
        const pollInterval = setInterval(async () => {
            try {
                const response = await httpRequest(`http://localhost:5002/api/projects/${projectId}/status`, { method: 'GET' });
                if (!response.ok) {
                    clearInterval(pollInterval);
                    this.postMessage({ type: 'error', content: '无法获取生成进度' });
                    return;
                }

                const status = await response.json() as ProjectStatusResponse;
                
                // 发送进度更新
                this.postMessage({
                    type: 'progress',
                    content: {
                        stage: status.current_stage,
                        progress: status.progress,
                        iteration: status.iteration,
                        message: status.message
                    }
                });
                
                // 获取当前文件列表，检测新文件
                try {
                    const filesResponse = await fetch(`http://localhost:5002/api/projects/${projectId}/files?include_content=true`);
                    if (filesResponse.ok) {
                        const filesData = await filesResponse.json() as FilesResponse;
                        const currentFiles = filesData.files || [];
                        
                        console.log(`[ProjectGen] 获取到 ${currentFiles.length} 个文件，已知 ${knownFiles.size} 个`);
                        
                        // 逐个发送新文件
                        for (const file of currentFiles) {
                            if (!knownFiles.has(file.path)) {
                                knownFiles.add(file.path);
                                console.log(`[ProjectGen] 新文件: ${file.path}`);
                                this.postMessage({
                                    type: 'newFile',
                                    content: {
                                        path: file.path,
                                        content: file.content || ''
                                    }
                                });
                            }
                        }
                    } else {
                        console.log(`[ProjectGen] 获取文件失败: ${filesResponse.status} ${filesResponse.statusText}`);
                    }
                } catch (e: any) {
                    console.log(`[ProjectGen] 获取文件异常: ${e.message}`);
                    // 如果获取文件失败，继续执行
                }

                // 检查是否完成
                if (status.status === 'completed') {
                    clearInterval(pollInterval);
                    this._currentProjectId = null;  // 清除当前项目 ID
                    await this.fetchGeneratedFiles(projectId, repo);
                } else if (status.status === 'failed') {
                    clearInterval(pollInterval);
                    this._currentProjectId = null;  // 清除当前项目 ID
                    this.postMessage({ type: 'error', content: `生成失败: ${status.error || status.message}` });
                } else if (status.status === 'cancelled') {
                    clearInterval(pollInterval);
                    this._currentProjectId = null;  // 清除当前项目 ID
                    this.postMessage({ type: 'info', content: `生成已取消: ${status.message}` });
                }
            } catch (error: any) {
                clearInterval(pollInterval);
                this.postMessage({ type: 'error', content: `进度查询失败: ${error.message}` });
            }
        }, 2000); // 每2秒轮询一次
    }

    private async fetchGeneratedFiles(projectId: string, repo: string) {
        try {
            const response = await fetch(`http://localhost:5002/api/projects/${projectId}/files`);
            if (!response.ok) {
                this.postMessage({ type: 'result', content: '✅ 项目生成完成！' });
                return;
            }

            const result = await response.json() as FilesResponse;
            this.postMessage({
                type: 'files',
                content: {
                    repo: repo,
                    files: result.files || [],
                    totalFiles: result.total_files || 0
                }
            });
        } catch (error: any) {
            this.postMessage({ type: 'result', content: '✅ 项目生成完成！' });
        }
    }

    private async handleOpenFile(data: any) {
        try {
            const filePath = data.filePath;  // 从前端传来的文件路径
            
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                vscode.window.showErrorMessage('请先打开一个工作区文件夹');
                return;
            }
            
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            
            // 直接使用 DevBench_outputs 中的实际文件
            // 文件路径格式: geotext/__init__.py 或 tmp_files/architecture_1.json
            // 需要组合成: DevBench_outputs/gpt-4o/{repo_name}/{file_path}
            
            if (!this._currentRepoName) {
                vscode.window.showErrorMessage('无法确定项目名称');
                return;
            }
            
            const actualPath = path.join(
                workspaceRoot, 
                'DevBench_outputs', 
                'gpt-4o', 
                this._currentRepoName,
                filePath
            );
            
            console.log(`[ProjectGen] 尝试打开文件: ${actualPath}`);
            
            if (!fs.existsSync(actualPath)) {
                vscode.window.showErrorMessage(`文件不存在: ${filePath}`);
                return;
            }
            
            // 在编辑器中打开文件
            const document = await vscode.workspace.openTextDocument(actualPath);
            await vscode.window.showTextDocument(document, { preview: false });
            
        } catch (error: any) {
            vscode.window.showErrorMessage(`打开文件失败: ${error.message}`);
        }
    }

    private handleNewSession() {
        this.postMessage({ type: 'info', content: '已开始新会话' });
    }

    private postMessage(message: any) {
        this._view?.webview.postMessage(message);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        // Get URIs for the built React app
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'dist', 'gui', 'assets', 'index.js')
        );
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'dist', 'gui', 'assets', 'style.css')
        );

        const nonce = this.getNonce();

        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} data:; connect-src http://localhost:5002 http://127.0.0.1:5002;">
    <link rel="stylesheet" type="text/css" href="${styleUri}">
    <title>ProjectGen</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            overflow: hidden;
        }
        #root {
            height: 100%;
            width: 100%;
        }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module" nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }

    private getNonce() {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }
}
