import * as vscode from 'vscode';
import { ProjectGenWebviewViewProvider } from './ProjectGenWebviewViewProvider';

export function activate(context: vscode.ExtensionContext) {
    console.log('ProjectGen extension activated');

    // Register webview view provider for sidebar
    const provider = new ProjectGenWebviewViewProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            ProjectGenWebviewViewProvider.viewType,
            provider,
            {
                webviewOptions: {
                    retainContextWhenHidden: true
                }
            }
        )
    );

    // Register command to focus chat
    const focusChatCommand = vscode.commands.registerCommand('projectgen.focusChat', () => {
        vscode.commands.executeCommand('projectgen.chatView.focus');
    });

    // Register command to start new session
    const newSessionCommand = vscode.commands.registerCommand('projectgen.newSession', () => {
        // TODO: Send message to webview to start new session
    });

    context.subscriptions.push(focusChatCommand, newSessionCommand);
}

export function deactivate() {}

