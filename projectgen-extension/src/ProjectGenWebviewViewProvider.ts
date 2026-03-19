import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';
import * as https from 'https';

interface ProjectGenResponse {
    error?: string;
    output_dir?: string;
    message?: string;
    status?: string;
    project_id?: string;
}

interface ProjectStatusResponse {
    project_id: string;
    repo_name?: string;
    output_dir?: string;
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
    output_dir?: string;
    files: GeneratedFile[];
    total_files: number;
    status: string;
}

interface ApiErrorPayload {
    status?: number;
    error_code?: string;
    message?: string;
    detail?: any;
}

// Helper function to make HTTP requests
function httpRequest(url: string, options: { method: string; headers?: Record<string, string>; body?: string }): Promise<{ ok: boolean; status: number; statusText: string; json: () => Promise<any>; text: () => Promise<string> }> {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const requestLib = urlObj.protocol === 'https:' ? https : http;
        const requestOptions: http.RequestOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
            path: urlObj.pathname + urlObj.search,
            method: options.method,
            headers: options.headers || {}
        };

        const req = requestLib.request(requestOptions, (res) => {
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

function extractApiErrorPayload(rawText: string): ApiErrorPayload | null {
    try {
        const parsed = JSON.parse(rawText);
        if (parsed && typeof parsed === 'object') {
            if (parsed.detail && typeof parsed.detail === 'object') {
                return parsed.detail as ApiErrorPayload;
            }
            return parsed as ApiErrorPayload;
        }
        return null;
    } catch {
        return null;
    }
}

async function formatApiError(response: { status: number; statusText: string; text: () => Promise<string> }): Promise<string> {
    const rawText = await response.text();
    const payload = extractApiErrorPayload(rawText);
    const statusPart = `${response.status} ${response.statusText}`.trim();

    if (payload?.message) {
        const codePart = payload.error_code ? ` [${payload.error_code}]` : '';
        return `服务器返回错误: ${statusPart}${codePart}\n${payload.message}`;
    }

    if (rawText) {
        return `服务器返回错误: ${statusPart}\n${rawText}`;
    }

    return `服务器返回错误: ${statusPart}`;
}

function normalizeErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message.trim()) {
        return error.message;
    }

    if (typeof error === 'string' && error.trim()) {
        return error;
    }

    try {
        const serialized = JSON.stringify(error);
        if (serialized && serialized !== '{}' && serialized !== 'null') {
            return serialized;
        }
    } catch {
        // ignore serialization errors and fallback to generic string
    }

    const fallback = String(error ?? '').trim();
    return fallback || '未知错误（未返回详细信息）';
}

function shouldShowConfigHint(errorMessage: string): boolean {
    const msg = errorMessage.toLowerCase();
    return msg.includes('econnrefused')
        || msg.includes('enotfound')
        || msg.includes('timed out')
        || msg.includes('invalid url')
        || msg.includes('repo_not_found');
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

    private _currentProjectId: string | null = null;
    private _currentRepoName: string | null = null;  // 跟踪当前项目名称
    private _currentOutputDir: string | null = null;

    private getServerUrl(): string {
        const configuredUrl = vscode.workspace.getConfiguration('projectgen').get<string>('serverUrl', 'http://localhost:5002');
        return (configuredUrl || 'http://localhost:5002').replace(/\/+$/, '');
    }

    private getServerOriginForCsp(): string {
        try {
            return new URL(this.getServerUrl()).origin;
        } catch {
            return 'http://localhost:5002';
        }
    }

    private async handleStopGeneration() {
        // 如果有正在生成的项目，通知服务器取消
        if (this._currentProjectId) {
            try {
                const response = await httpRequest(`${this.getServerUrl()}/api/projects/${this._currentProjectId}/cancel`, {
                    method: 'POST',
                });

                if (!response.ok) {
                    throw new Error(await formatApiError(response));
                }

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
        this.postMessage({ type: 'error', content: '请使用命令格式：/projectgen repo=<路径>' });
    }

    private async handleGenerateFromRepo(data: any) {
        console.log('[ProjectGen] handleGenerateFromRepo called with data:', data);
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            this.postMessage({ type: 'error', content: '请先打开一个工作区文件夹' });
            return;
        }

        const repoInput = String(data.repo || '');
        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        const trimmedRepoInput = repoInput.trim();

        if (!trimmedRepoInput) {
            this.postMessage({ type: 'error', content: 'repo 路径不能为空' });
            return;
        }

        const resolvedPreviewPath = path.isAbsolute(trimmedRepoInput)
            ? path.resolve(trimmedRepoInput)
            : path.resolve(workspaceRoot, trimmedRepoInput);
        console.log('[ProjectGen] Processing repo path:', resolvedPreviewPath);

        try {
            this.postMessage({ type: 'info', content: `正在从路径生成项目: ${resolvedPreviewPath}` });

            const response = await httpRequest(`${this.getServerUrl()}/api/projects/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_path: trimmedRepoInput,
                    workspace_root: workspaceRoot,
                    requirement: data.message || `Generate project for ${path.basename(resolvedPreviewPath)}`,
                    model: 'gpt-4o'
                })
            });

            if (!response.ok) {
                throw new Error(await formatApiError(response));
            }

            const result = await response.json() as any;
            
            if (result.project_id) {
                this._currentProjectId = result.project_id;
                this._currentRepoName = result.repo_name || path.basename(resolvedPreviewPath);
                this._currentOutputDir = result.output_dir || null;
                this.pollProgress(result.project_id, repoInput);
            } else {
                this.postMessage({ type: 'error', content: `生成失败: 服务器返回格式错误` });
            }
        } catch (error: unknown) {
            const errorMessage = normalizeErrorMessage(error);
            const configHint = shouldShowConfigHint(errorMessage)
                ? '\n\n请检查服务地址配置（projectgen.serverUrl）和 repo 路径'
                : '';

            this.postMessage({ 
                type: 'error', 
                content: `请求失败: ${errorMessage}${configHint}` 
            });
        }
    }

    private async pollProgress(projectId: string, repo: string) {
        let knownFiles = new Set<string>();
        
        const pollInterval = setInterval(async () => {
            try {
                const response = await httpRequest(`${this.getServerUrl()}/api/projects/${projectId}/status`, {
                    method: 'GET',
                });
                if (!response.ok) {
                    clearInterval(pollInterval);
                    this.postMessage({ type: 'error', content: await formatApiError(response) });
                    return;
                }

                const status = await response.json() as ProjectStatusResponse;

                if (status.repo_name) {
                    this._currentRepoName = status.repo_name;
                }
                if (status.output_dir) {
                    this._currentOutputDir = status.output_dir;
                }
                
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
                    const filesResponse = await httpRequest(`${this.getServerUrl()}/api/projects/${projectId}/files?include_content=true`, {
                        method: 'GET',
                    });
                    if (filesResponse.ok) {
                        const filesData = await filesResponse.json() as FilesResponse;
                        if (filesData.repo_name) {
                            this._currentRepoName = filesData.repo_name;
                        }
                        if (filesData.output_dir) {
                            this._currentOutputDir = filesData.output_dir;
                        }
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
                        console.log(`[ProjectGen] 获取文件失败: ${await formatApiError(filesResponse)}`);
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
            const response = await httpRequest(`${this.getServerUrl()}/api/projects/${projectId}/files`, {
                method: 'GET',
            });
            if (!response.ok) {
                this.postMessage({ type: 'error', content: await formatApiError(response) });
                return;
            }

            const result = await response.json() as FilesResponse;
            if (result.repo_name) {
                this._currentRepoName = result.repo_name;
            }
            if (result.output_dir) {
                this._currentOutputDir = result.output_dir;
            }

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
            if (!this._currentOutputDir) {
                vscode.window.showErrorMessage('无法确定输出目录，请先开始生成任务');
                return;
            }

            const baseDir = path.resolve(this._currentOutputDir);
            const normalizedPath = path.resolve(baseDir, filePath);
            const basePrefix = `${baseDir}${path.sep}`;

            if (normalizedPath !== baseDir && !normalizedPath.startsWith(basePrefix)) {
                vscode.window.showErrorMessage('非法文件路径，已阻止访问');
                return;
            }
            
            console.log(`[ProjectGen] 尝试打开文件: ${normalizedPath}`);
            
            if (!fs.existsSync(normalizedPath)) {
                vscode.window.showErrorMessage(`文件不存在: ${filePath}`);
                return;
            }
            
            // 在编辑器中打开文件
            const document = await vscode.workspace.openTextDocument(normalizedPath);
            await vscode.window.showTextDocument(document, { preview: false });
            
        } catch (error: any) {
            vscode.window.showErrorMessage(`打开文件失败: ${error.message}`);
        }
    }

    private handleNewSession() {
        this._currentProjectId = null;
        this._currentRepoName = null;
        this._currentOutputDir = null;
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
        const serverOrigin = this.getServerOriginForCsp();

        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} data:; connect-src ${serverOrigin};">
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
