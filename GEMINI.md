# Sobre o Projeto

Este projeto cria um assistente de codificação autônomo que opera dentro do Visual Studio Code. Ele consiste em uma extensão do VS Code que fornece uma interface de chat e um backend em Python que usa uma equipe de agentes de IA (construídos com a biblioteca `crewai`) para gerar, testar, refatorar e **modificar código diretamente no seu workspace do VS Code**.

## Capacidades Chave

- **Feedback em Tempo Real:** Utiliza WebSockets para fornecer um streaming de logs em tempo real, permitindo que você acompanhe o progresso dos agentes passo a passo.
- **Desenvolvimento Orientado a Agentes:** Utiliza uma equipe de agentes especializados (Gerente, Desenvolvedor, QA, Refatorador) para simular um fluxo de trabalho de desenvolvimento de software.
- **Ciclo de Teste e Depuração:** Cria testes, escreve código para passá-los e tenta corrigir o código automaticamente se os testes falharem.
- **Modificação de Código Existente:** Pode receber tarefas para alterar ou adicionar funcionalidades a arquivos já existentes no seu projeto.

# Tecnologias Chave

- **Backend:** Python, Flask, CrewAI
- **Frontend:** Visual Studio Code Extension, TypeScript, Webview (HTML/CSS/JS)
- **Comunicação:** WebSockets (via Flask-SocketIO)

# Estrutura do Projeto

- `gerador_de_agentes.py`: Define as personalidades, ferramentas e capacidades de cada agente da equipe.
- `api.py`: Cria um servidor Flask que orquestra o fluxo de trabalho dos agentes (Planejamento -> Teste -> Desenvolvimento -> Depuração -> Refatoração).
- `extension.ts`: O código-fonte da extensão do VS Code. Ele cria a interface de chat e se comunica com o backend.
- `requirements.txt`: Lista as dependências Python do projeto.
- `.env.example`: Arquivo de exemplo para configuração de chaves de API.
- `GEMINI.md`: Este arquivo, fornecendo uma visão geral do projeto.

# Como Executar

### 1. Backend (Servidor Python)

a. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

b. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

c. **Configure sua chave de API:**
   - Renomeie o arquivo `.env.example` para `.env`.
   - Adicione sua chave de API ao arquivo `.env` (ex: `OPENAI_API_KEY="sk-..."`).

e. **Execute o servidor da API:**
   ```bash
   python api.py
   ```
   O servidor estará rodando em `http://127.0.0.1:5001`.

### 2. Frontend (Extensão VS Code)

a. **Instale as dependências do Node.js (se ainda não o fez):**
   ```bash
   npm install
   ```

b. **Execute a extensão:**
   - Abra este projeto no VS Code.
   - Pressione `F5` para iniciar o "Extension Development Host". Uma nova janela do VS Code será aberta com a extensão em execução.

# Como Usar

1. Na nova janela do VS Code (aberta ao pressionar `F5`), **abra a pasta do projeto que você deseja modificar**.
2. Abra a paleta de comandos (`Ctrl+Shift+P` ou `Cmd+Shift+P`).
3. Procure e execute o comando `Auto Coder: Start Chat`.
4. Uma nova aba de chat aparecerá. Agora você pode fazer pedidos que interagem com seu projeto.

**Exemplos de Prompts:**
- **Para criar algo novo:** "Crie uma função em um novo arquivo chamado `calculadora.py` que some dois números e crie os testes para ela."
- **Para modificar algo existente:** "Eu tenho um arquivo `api.py`. Adicione um novo endpoint chamado `/status` que retorne `{'status': 'ok'}`."
- **Para refatorar:** "Analise o arquivo `utils.py` e refatore a função `process_data` para ser mais eficiente."