import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

const SERVER_URL = 'http://localhost:5002';

export class ProjectGenPanel {
    public static currentPanel: ProjectGenPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (ProjectGenPanel.currentPanel) {
            ProjectGenPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'projectgen',
            'ProjectGen',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        ProjectGenPanel.currentPanel = new ProjectGenPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._panel.webview.html = this._getHtmlForWebview();

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.command) {
                    case 'generate':
                        await this.handleGenerate(message.data);
                        break;
                }
            },
            null,
            this._disposables
        );

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    private async handleGenerate(data: {
        repo?: string;
        dataset?: string;
        model?: string;
        project?: string;
    }) {
        try {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                this.sendMessage({ type: 'error', message: 'No workspace folder opened' });
                return;
            }

            const workspaceDir = workspaceFolders[0].uri.fsPath;
            let projectDir: string;
            let actualRepo: string;
            let actualDataset: string;

            // 处理 project 参数
            if (data.project) {
                this.sendMessage({ type: 'log', message: 'Searching for projects...' });
                const searchRoot = path.join(workspaceDir, data.project);
                const foundProjects = await this.findProjects(searchRoot);

                if (foundProjects.length === 0) {
                    this.sendMessage({ type: 'error', message: `No valid projects found in ${data.project}` });
                    return;
                }

                if (foundProjects.length > 1) {
                    this.sendMessage({ 
                        type: 'error', 
                        message: `Found ${foundProjects.length} projects. Please specify one using repo parameter.` 
                    });
                    return;
                }

                projectDir = foundProjects[0].fullPath;
                actualRepo = foundProjects[0].name;
                actualDataset = foundProjects[0].dataset;
            } else {
                projectDir = path.join(workspaceDir, 'datasets', data.dataset || 'CodeProjectEval', data.repo || '');
                actualRepo = data.repo || '';
                actualDataset = data.dataset || 'CodeProjectEval';
            }

            this.sendMessage({ type: 'log', message: `Repository: ${actualRepo}` });
            this.sendMessage({ type: 'log', message: `Dataset: ${actualDataset}` });
            this.sendMessage({ type: 'log', message: `Model: ${data.model || 'gpt-4o'}` });

            // 读取 config.json
            const configPath = path.join(projectDir, 'config.json');
            const configContent = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configContent);

            // 读取 PRD
            const prdPath = path.join(projectDir, config.PRD);
            const requirement = fs.readFileSync(prdPath, 'utf-8');

            this.sendMessage({ type: 'log', message: 'Connecting to server...' });

            // 连接服务器
            const healthResponse = await fetch(`${SERVER_URL}/api/health`);
            if (!healthResponse.ok) {
                throw new Error('Cannot connect to server');
            }

            this.sendMessage({ type: 'log', message: 'Server connected' });
            this.sendMessage({ type: 'log', message: 'Starting generation...' });

            // 启动生成任务
            const generateResponse = await fetch(`${SERVER_URL}/api/projects/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: actualDataset,
                    repo_name: actualRepo,
                    requirement: requirement,
                    uml_class: '',
                    uml_sequence: '',
                    arch_design: '',
                    model: data.model || 'gpt-4o',
                    code_file_DAG: config.code_file_DAG || []
                })
            });

            const generateData = await generateResponse.json() as any;
            const projectId = generateData.project_id;

            this.sendMessage({ type: 'log', message: `Project ID: ${projectId}` });
            this.sendMessage({ type: 'progress', stage: 'starting', progress: 0 });

            // 轮询进度
            await this.pollProgress(projectId, workspaceDir, actualDataset, actualRepo);

        } catch (error: any) {
            this.sendMessage({ type: 'error', message: error.message });
        }
    }

    private async pollProgress(projectId: string, workspaceDir: string, dataset: string, repo: string) {
        let isComplete = false;

        while (!isComplete) {
            await new Promise(resolve => setTimeout(resolve, 3000));

            try {
                const response = await fetch(`${SERVER_URL}/api/projects/${projectId}/status`);
                const statusData = await response.json() as any;

                this.sendMessage({
                    type: 'progress',
                    stage: statusData.current_stage,
                    progress: statusData.progress,
                    iteration: statusData.iteration
                });

                if (statusData.status === 'completed') {
                    isComplete = true;
                    this.sendMessage({ type: 'log', message: 'Generation completed!' });

                    // 获取生成的文件
                    const filesResponse = await fetch(`${SERVER_URL}/api/projects/${projectId}/files`);
                    const filesData = await filesResponse.json() as any;
                    const files = filesData.files;

                    // 写入文件
                    const outputDir = path.join(workspaceDir, `${dataset}_outputs`, repo);
                    for (const file of files) {
                        const fullPath = path.join(outputDir, file.path);
                        const dir = path.dirname(fullPath);
                        if (!fs.existsSync(dir)) {
                            fs.mkdirSync(dir, { recursive: true });
                        }
                        fs.writeFileSync(fullPath, file.content, 'utf-8');
                    }

                    this.sendMessage({ type: 'complete', fileCount: files.length, outputDir });

                } else if (statusData.status === 'failed') {
                    this.sendMessage({ type: 'error', message: statusData.error || 'Unknown error' });
                    break;
                }
            } catch (error: any) {
                this.sendMessage({ type: 'error', message: `Status check failed: ${error.message}` });
                break;
            }
        }
    }

    private async findProjects(rootPath: string): Promise<Array<{fullPath: string; name: string; dataset: string}>> {
        const projects: Array<{fullPath: string; name: string; dataset: string}> = [];

        const searchDir = async (dirPath: string, relativePath: string[] = []) => {
            try {
                const entries = fs.readdirSync(dirPath, { withFileTypes: true });
                const hasConfig = entries.some(e => e.name === 'config.json' && e.isFile());

                if (hasConfig) {
                    try {
                        const configPath = path.join(dirPath, 'config.json');
                        const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
                        
                        if (config.PRD) {
                            const prdPath = path.join(dirPath, config.PRD);
                            if (fs.existsSync(prdPath)) {
                                const parts = relativePath;
                                let dataset = 'Unknown';
                                let name = parts[parts.length - 1] || 'unknown';

                                const datasetIdx = parts.indexOf('datasets');
                                if (datasetIdx >= 0 && parts.length > datasetIdx + 1) {
                                    dataset = parts[datasetIdx + 1];
                                    if (parts.length > datasetIdx + 2) {
                                        name = parts[datasetIdx + 2];
                                    }
                                }

                                projects.push({ fullPath: dirPath, name, dataset });
                            }
                        }
                    } catch {}
                }

                for (const entry of entries) {
                    if (entry.isDirectory() && !['node_modules', '.git', '__pycache__', 'dist', 'build'].includes(entry.name)) {
                        await searchDir(path.join(dirPath, entry.name), [...relativePath, entry.name]);
                    }
                }
            } catch {}
        };

        await searchDir(rootPath);
        return projects;
    }

    private sendMessage(message: any) {
        this._panel.webview.postMessage(message);
    }

    private _getHtmlForWebview(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProjectGen</title>
    <style>
        /* Continue-style base styles */
        html, body {
            height: 100%;
            line-height: 1.3;
            background-color: var(--vscode-editor-background);
            font-family: var(--vscode-font-family);
            margin: 0;
            padding: 0;
        }
        
        body {
            color: var(--vscode-editor-foreground);
        }
        
        *:focus {
            outline: none;
        }
        
        /* Thin scrollbar like Continue */
        .thin-scrollbar {
            scrollbar-width: thin;
        }
        
        .thin-scrollbar::-webkit-scrollbar {
            width: 8px;
        }
        
        .thin-scrollbar::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .thin-scrollbar::-webkit-scrollbar-thumb {
            background-color: var(--vscode-scrollbarSlider-background);
            border-radius: 4px;
        }
        
        .thin-scrollbar::-webkit-scrollbar-thumb:hover {
            background-color: var(--vscode-scrollbarSlider-hoverBackground);
        }
        
        /* Container */
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Typography */
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 24px;
            color: var(--vscode-editor-foreground);
        }
        
        /* Form elements */
        .form-group {
            margin-bottom: 16px;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            font-size: 13px;
            color: var(--vscode-foreground);
        }
        
        input {
            width: 100%;
            padding: 8px 10px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 2px;
            font-family: var(--vscode-font-family);
            font-size: 13px;
            box-sizing: border-box;
        }
        
        input:focus {
            outline: 1px solid var(--vscode-focusBorder);
            outline-offset: -1px;
        }
        
        input::placeholder {
            color: var(--vscode-input-placeholderForeground);
        }
        
        /* Button - Continue style */
        button {
            padding: 8px 16px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 2px;
            cursor: pointer;
            font-size: 13px;
            font-family: var(--vscode-font-family);
            font-weight: 500;
            transition: background-color 0.1s;
        }
        
        button:hover:not(:disabled) {
            background: var(--vscode-button-hoverBackground);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        /* Output panel - Continue style */
        .output {
            margin-top: 24px;
            padding: 16px;
            background: var(--vscode-editor-background);
            border: 2px solid var(--vscode-panel-border);
            border-radius: 4px;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .log-line {
            margin: 4px 0;
            font-family: var(--vscode-editor-font-family), 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.5;
        }
        
        .error {
            color: var(--vscode-errorForeground);
        }
        
        /* Progress bar - Continue style */
        .progress {
            margin: 12px 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 24px;
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--vscode-button-background);
            transition: width 0.3s ease;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-weight: 600;
            font-size: 12px;
            color: var(--vscode-editor-foreground);
        }
        
        .stage-info {
            margin-top: 8px;
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ProjectGen - Multi-Agent Project Generation</h1>
        
        <div class="form-group">
            <label for="repo">Repository Name</label>
            <input type="text" id="repo" placeholder="e.g., bplustree">
        </div>
        
        <div class="form-group">
            <label for="dataset">Dataset (optional)</label>
            <input type="text" id="dataset" placeholder="CodeProjectEval" value="CodeProjectEval">
        </div>
        
        <div class="form-group">
            <label for="model">Model (optional)</label>
            <input type="text" id="model" placeholder="gpt-4o" value="gpt-4o">
        </div>
        
        <div class="form-group">
            <label for="project">Or Project Path (recursive search)</label>
            <input type="text" id="project" placeholder="e.g., datasets">
        </div>
        
        <button id="generateBtn">Generate Project</button>
        
        <div class="output thin-scrollbar" id="output" style="display: none;">
            <div class="progress" id="progressContainer" style="display: none;">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    <div class="progress-text" id="progressText">0%</div>
                </div>
                <div class="stage-info" id="stageInfo"></div>
            </div>
            <div id="logs"></div>
        </div>
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        const generateBtn = document.getElementById('generateBtn');
        const output = document.getElementById('output');
        const logs = document.getElementById('logs');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const stageInfo = document.getElementById('stageInfo');
        
        generateBtn.addEventListener('click', () => {
            const repo = document.getElementById('repo').value.trim();
            const dataset = document.getElementById('dataset').value.trim();
            const model = document.getElementById('model').value.trim();
            const project = document.getElementById('project').value.trim();
            
            if (!repo && !project) {
                alert('Please specify either a repository name or a project path');
                return;
            }
            
            output.style.display = 'block';
            logs.innerHTML = '';
            progressContainer.style.display = 'none';
            generateBtn.disabled = true;
            
            vscode.postMessage({
                command: 'generate',
                data: { repo, dataset, model, project }
            });
        });
        
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'log':
                    addLog(message.message);
                    break;
                case 'error':
                    addLog(message.message, 'error');
                    generateBtn.disabled = false;
                    break;
                case 'progress':
                    progressContainer.style.display = 'block';
                    progressFill.style.width = message.progress + '%';
                    progressText.textContent = message.progress + '%';
                    if (message.stage) {
                        stageInfo.textContent = \`Stage: \${message.stage} (Iteration \${message.iteration || 0})\`;
                    }
                    break;
                case 'complete':
                    addLog(\`Completed! Generated \${message.fileCount} files\`);
                    addLog(\`Output directory: \${message.outputDir}\`);
                    generateBtn.disabled = false;
                    break;
            }
        });
        
        function addLog(text, className = '') {
            const line = document.createElement('div');
            line.className = 'log-line ' + className;
            line.textContent = text;
            logs.appendChild(line);
            logs.scrollTop = logs.scrollHeight;
        }
    </script>
</body>
</html>`;
    }

    public dispose() {
        ProjectGenPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const disposable = this._disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }
}
