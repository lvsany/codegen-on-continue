import * as vscode from 'vscode';

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
                vscode.Uri.joinPath(this._extensionUri, 'gui'),
            ]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'generate':
                    await this.handleGenerate(data);
                    break;
            }
        });
    }

    private async handleGenerate(data: any) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            this.postMessage({ type: 'error', message: 'No workspace folder opened' });
            return;
        }

        try {
            // Call projectgen server
            const response = await fetch('http://localhost:5002/api/projects/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            this.postMessage({ type: 'result', data: result });
        } catch (error: any) {
            this.postMessage({ type: 'error', message: error.message });
        }
    }

    private postMessage(message: any) {
        this._view?.webview.postMessage(message);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        // Check if we're in development mode
        const isDevelopment = process.env.NODE_ENV === 'development';
        
        let scriptUri: string;
        let styleUri: string;

        if (isDevelopment) {
            // Development mode - use Vite dev server
            scriptUri = 'http://localhost:5173/src/main.tsx';
            styleUri = 'http://localhost:5173/src/index.css';
        } else {
            // Production mode - use built assets
            scriptUri = webview.asWebviewUri(
                vscode.Uri.joinPath(this._extensionUri, 'gui', 'assets', 'index.js')
            ).toString();
            styleUri = webview.asWebviewUri(
                vscode.Uri.joinPath(this._extensionUri, 'gui', 'assets', 'index.css')
            ).toString();
        }

        const nonce = this.getNonce();
        const vscMediaUrl = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'gui')
        ).toString();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; 
        img-src ${webview.cspSource} https: data:; 
        script-src ${isDevelopment ? "'unsafe-inline' 'unsafe-eval' http://localhost:5173" : `'nonce-${nonce}'`} ${webview.cspSource};
        style-src ${webview.cspSource} ${isDevelopment ? "'unsafe-inline' http://localhost:5173" : `'nonce-${nonce}'`};
        font-src ${webview.cspSource};
        connect-src ${isDevelopment ? 'http://localhost:5173 ws://localhost:5173' : ''} http://localhost:5002;">
    
    <script>const vscode = acquireVsCodeApi();</script>
    <link href="${styleUri}" rel="stylesheet">
    <title>ProjectGen</title>
</head>
<body>
    <div id="root"></div>
    
    ${isDevelopment ? `
    <script type="module">
        import RefreshRuntime from "http://localhost:5173/@react-refresh"
        RefreshRuntime.injectIntoGlobalHook(window)
        window.$RefreshReg$ = () => {}
        window.$RefreshSig$ = () => (type) => type
        window.__vite_plugin_react_preamble_installed__ = true
    </script>
    ` : ''}
    
    <script type="module" nonce="${nonce}" src="${scriptUri}"></script>
    <script>window.vscMediaUrl = "${vscMediaUrl}"</script>
    <script>window.ide = "vscode"</script>
    <script>localStorage.setItem("ide", '"vscode"')</script>
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
