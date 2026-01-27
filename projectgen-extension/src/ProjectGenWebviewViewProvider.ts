import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

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

    private handleStopGeneration() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        this.postMessage({ type: 'info', content: 'Generation stopped' });
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
            const response = await fetch('http://localhost:5002/api/projects/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: 'DevBench',
                    repo_name: 'example-project',  // 默认项目名
                    requirement: userMessage,
                    model: 'gpt-4o'
                })
            });

            if (!response.ok) {
                throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`);
            }

            const result = await response.json() as ProjectGenResponse;
            
            if (result.error) {
                this.postMessage({ type: 'error', content: `生成失败: ${result.error}` });
            } else {
                this.postMessage({ 
                    type: 'result', 
                    content: `✅ 项目生成成功！\n\n生成的文件保存在: ${result.output_dir || workspaceRoot}\n\n${result.message || ''}` 
                });
            }
        } catch (error: any) {
            this.postMessage({ 
                type: 'error', 
                content: `连接失败: ${error.message}\n\n请确保 ProjectGen 服务器正在运行 (http://localhost:5002)` 
            });
        }
    }

    private async handleGenerateFromRepo(data: any) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            this.postMessage({ type: 'error', content: '请先打开一个工作区文件夹' });
            return;
        }

        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        const repo = data.repo;

        try {
            this.postMessage({ type: 'info', content: `正在从 ${repo} 仓库生成项目...` });

            const response = await fetch('http://localhost:5002/api/projects/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: 'CodeProjectEval',
                    repo_name: repo,
                    requirement: `Generate project for ${repo}`,
                    model: 'gpt-4o'
                })
            });

            if (!response.ok) {
                throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`);
            }

            const result = await response.json() as ProjectGenResponse;
            
            if (result.error) {
                this.postMessage({ type: 'error', content: `生成失败: ${result.error}` });
            } else {
                const projectId = (result as any).project_id;
                if (projectId) {
                    // 开始轮询进度
                    this.pollProgress(projectId, repo);
                } else {
                    this.postMessage({ 
                        type: 'result', 
                        content: `✅ 项目生成成功！\n\n仓库: ${repo}\n生成的文件保存在: ${result.output_dir || workspaceRoot}\n\n${result.message || ''}` 
                    });
                }
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
                const response = await fetch(`http://localhost:5002/api/projects/${projectId}/status`);
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
                    await this.fetchGeneratedFiles(projectId, repo);
                } else if (status.status === 'failed') {
                    clearInterval(pollInterval);
                    this.postMessage({ type: 'error', content: `生成失败: ${status.error || status.message}` });
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
            const filePath = data.filePath;
            const content = data.content;
            
            // 创建临时文件并打开
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                vscode.window.showErrorMessage('请先打开一个工作区文件夹');
                return;
            }
            
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            const fullPath = path.join(workspaceRoot, 'generated', filePath);
            
            // 确保目录存在
            const dir = path.dirname(fullPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            
            // 写入文件内容
            fs.writeFileSync(fullPath, content, 'utf8');
            
            // 在编辑器中打开文件
            const document = await vscode.workspace.openTextDocument(fullPath);
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
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}' 'unsafe-inline'; img-src ${webview.cspSource} data:; connect-src http://localhost:5002;">
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
    <script nonce="${nonce}">
        (function() {
            function loadScript() {
                var root = document.getElementById('root');
                if (!root) {
                    console.error('Root element not found, retrying...');
                    setTimeout(loadScript, 50);
                    return;
                }
                var script = document.createElement('script');
                script.src = '${scriptUri}';
                script.nonce = '${nonce}';
                document.body.appendChild(script);
            }
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                setTimeout(loadScript, 0);
            } else {
                document.addEventListener('DOMContentLoaded', loadScript);
            }
        })();
    </script>
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
