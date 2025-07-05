"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const socket_io_client_1 = require("socket.io-client");
function activate(context) {
    // Configurações do usuário
    const cfg = vscode.workspace.getConfiguration('autocoder');
    const serverUrl = cfg.get('serverUrl', 'http://127.0.0.1:5001');
    // Cria um item na Status Bar para abrir o chat rapidamente
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(robot) Auto Coder: $(sync~spin) Conectando';
    statusBarItem.command = 'autocoder.startChat';
    statusBarItem.tooltip = 'Abrir chat do Auto Coder';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // Comando principal para abrir o chat
    let disposable = vscode.commands.registerCommand('autocoder.startChat', () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage("Por favor, abra uma pasta ou workspace primeiro.");
            return;
        }
        const projectDir = workspaceFolders[0].uri.fsPath;
        const panel = vscode.window.createWebviewPanel('autoCoderChat', 'Auto Coder Chat', vscode.ViewColumn.One, {
            enableScripts: true,
            // Manter o conteúdo do webview vivo mesmo quando não está visível
            retainContextWhenHidden: true
        });
        panel.webview.html = getWebviewContent();
        // Conectar ao servidor WebSocket
        const socket = (0, socket_io_client_1.io)(serverUrl, {
            reconnectionAttempts: 3,
            timeout: 5000,
        });
        socket.on('connect_error', (err) => {
            statusBarItem.text = '$(error) Auto Coder: Offline';
            vscode.window.showErrorMessage(`Auto Coder – falha na conexão: ${err.message}`);
        });
        socket.io.on('reconnect_attempt', (attempt) => {
            statusBarItem.text = `$(sync~spin) Auto Coder: Reconectando (${attempt})`;
        });
        socket.io.on('reconnect_failed', () => {
            statusBarItem.text = '$(error) Auto Coder: Reconexão falhou';
        });
        socket.on('connect', () => {
            statusBarItem.text = '$(robot) Auto Coder: Online';
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
            socket.disconnect();
            statusBarItem.text = '$(debug-disconnect) Auto Coder: Desconectado';
        });
        panel.webview.onDidReceiveMessage(message => {
            if (message.command === 'sendMessage') {
                panel.webview.postMessage({ command: 'addMessage', role: 'user', text: message.text });
                socket.emit('start_crew', {
                    prompt: message.text,
                    project_dir: projectDir
                });
            }
        }, undefined, context.subscriptions);
        // Garantir que o socket seja desconectado quando o painel for fechado
        panel.onDidDispose(() => {
            socket.disconnect();
            statusBarItem.text = '$(debug-disconnect) Auto Coder: Desconectado';
        }, null, context.subscriptions);
    });
    context.subscriptions.push(disposable);
    // --- Inline Completion Provider (estilo GitHub Copilot) ---
    const inlineProvider = {
        async provideInlineCompletionItems(document, position) {
            try {
                const linePrefix = document.lineAt(position).text.substring(0, position.character);
                // Só faz requisição se há texto no prefixo
                if (linePrefix.trim().length === 0) {
                    return { items: [] };
                }
                // Envia para o backend (ou outro endpoint) o prefixo e obtém sugestão
                const response = await fetchWithRetry(`${serverUrl}/inline_completion`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prefix: linePrefix,
                        language: document.languageId,
                        filePath: document.uri.fsPath
                    })
                });
                if (!response.ok) {
                    let humanMsg = `Auto Coder – erro ${response.status}`;
                    if (response.status === 401) {
                        humanMsg = 'Auto Coder – chave API inválida ou ausente.';
                    }
                    else if (response.status === 429) {
                        humanMsg = 'Auto Coder – limite de requisições excedido (rate-limit).';
                    }
                    else if (response.status >= 500) {
                        humanMsg = 'Auto Coder – erro interno no servidor.';
                    }
                    vscode.window.showWarningMessage(humanMsg);
                    statusBarItem.text = '$(error) Auto Coder';
                    return { items: [] };
                }
                const data = await response.json();
                const suggestion = data.completion;
                if (!suggestion) {
                    return { items: [] };
                }
                const range = new vscode.Range(position, position);
                return {
                    items: [
                        {
                            insertText: suggestion,
                            range
                        }
                    ]
                };
            }
            catch (err) {
                vscode.window.showErrorMessage(`Auto Coder – falha ao obter sugestão: ${String(err)}`);
                statusBarItem.text = '$(error) Auto Coder';
                return { items: [] };
            }
        }
    };
    context.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, inlineProvider));
    // --- Utilitários ---
    async function fetchWithRetry(url, options, retries = 2) {
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const res = await fetch(url, options);
                if (res.ok) {
                    return res;
                }
            }
            catch (err) {
                if (attempt === retries) {
                    throw err;
                }
            }
            // Espera incremental (exponencial simples)
            await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
        }
        // Nunca deve chegar aqui
        throw new Error('Unexpected fetchWithRetry failure');
    }
}
function getWebviewContent() {
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
function deactivate() { }
//# sourceMappingURL=extension.js.map