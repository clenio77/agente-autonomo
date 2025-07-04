import * as vscode from 'vscode';
import { io, Socket } from 'socket.io-client';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('autocoder.startChat', () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage("Por favor, abra uma pasta ou workspace primeiro.");
            return;
        }
        const projectDir = workspaceFolders[0].uri.fsPath;

        const panel = vscode.window.createWebviewPanel(
            'autoCoderChat',
            'Auto Coder Chat',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                // Manter o conteúdo do webview vivo mesmo quando não está visível
                retainContextWhenHidden: true 
            }
        );

        panel.webview.html = getWebviewContent();

        // Conectar ao servidor WebSocket
        const socket = io('http://127.0.0.1:5001');

        socket.on('connect', () => {
            panel.webview.postMessage({ command: 'addMessage', role: 'agent', text: 'Conectado ao servidor de agentes! O que vamos construir hoje?' });
        });

        socket.on('log_message', (message) => {
            panel.webview.postMessage({ command: 'addMessage', role: 'agent', text: message.data });
        });

        socket.on('crew_finished', (message) => {
            const finalText = `**PROCESSO CONCLUÍDO**\n\n**Status:** ${message.status}\n\n**Resultado Final:**\n---\n${message.result}`;
            panel.webview.postMessage({ command: 'addMessage', role: 'agent', text: finalText });
        });

        socket.on('disconnect', () => {
            panel.webview.postMessage({ command: 'addMessage', role: 'agent', text: 'Desconectado do servidor de agentes.' });
        });

        panel.webview.onDidReceiveMessage(
            message => {
                if (message.command === 'sendMessage') {
                    panel.webview.postMessage({ command: 'addMessage', role: 'user', text: message.text });
                    socket.emit('start_crew', { 
                        prompt: message.text, 
                        project_dir: projectDir 
                    });
                }
            },
            undefined,
            context.subscriptions
        );

        // Garantir que o socket seja desconectado quando o painel for fechado
        panel.onDidDispose(() => {
            socket.disconnect();
        }, null, context.subscriptions);
    });

    context.subscriptions.push(disposable);
}

function getWebviewContent(): string {
    // O HTML e CSS permanecem os mesmos
    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Auto Coder Chat</title>
        <style>
            body { font-family: sans-serif; padding: 10px; }
            #chat-container { display: flex; flex-direction: column; height: 95vh; }
            #messages { flex-grow: 1; overflow-y: auto; border: 1px solid #333; padding: 10px; margin-bottom: 10px; white-space: pre-wrap; }
            .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; }
            .user { background-color: #007acc; color: white; align-self: flex-end; }
            .agent { background-color: #333; color: white; align-self: flex-start; }
            #input-form { display: flex; }
            #input-text { flex-grow: 1; }
        </style>
    </head>
    <body>
        <div id="chat-container">
            <div id="messages"></div>
            <form id="input-form">
                <input type="text" id="input-text" placeholder="Escreva o seu pedido aqui..." />
                <button type="submit">Enviar</button>
            </form>
        </div>

        <script>
            const vscode = acquireVsCodeApi();
            const messagesDiv = document.getElementById('messages');
            const form = document.getElementById('input-form');
            const input = document.getElementById('input-text');

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const text = input.value;
                if (text) {
                    vscode.postMessage({ command: 'sendMessage', text: text });
                    input.value = '';
                }
            });

            window.addEventListener('message', event => {
                const message = event.data;
                const messageElement = document.createElement('div');
                messageElement.className = 'message ' + message.role;
                messageElement.textContent = message.text;
                messagesDiv.appendChild(messageElement);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            });
        </script>
    </body>
    </html>`;
}

export function deactivate() {}