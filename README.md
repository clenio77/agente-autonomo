# Auto-Coder: Uma Equipe de Agentes de IA para Desenvolvimento de Software

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Auto-Coder** é um protótipo avançado que integra uma equipe de agentes de Inteligência Artificial diretamente no Visual Studio Code. Em vez de um simples assistente de autocompletar, este projeto implementa um fluxo de trabalho de desenvolvimento de software completo e autônomo, onde agentes especializados colaboram para entender, planejar, desenvolver, testar e refatorar código com base em solicitações em linguagem natural.

O sistema tem **consciência do contexto do seu projeto**, permitindo que ele modifique arquivos existentes ou crie novos de forma inteligente.

---

## ✨ Funcionalidades Chave

- **Equipe de Agentes Autônomos:** Utiliza a biblioteca `CrewAI` para orquestrar uma equipe com diferentes papéis:
  - **Gerente de Projetos:** Analisa o código existente e cria um plano de ação.
  - **Engenheiro de QA:** Escreve os testes unitários primeiro (TDD).
  - **Desenvolvedor Sênior:** Escreve o código para passar nos testes.
  - **Especialista em Refatoração:** Melhora a qualidade do código após a validação.
- **Consciência de Contexto:** Antes de qualquer ação, o Gerente de Projetos analisa a estrutura de arquivos e o conteúdo do seu workspace para tomar decisões informadas.
- **Ciclo de Desenvolvimento e Depuração Automatizado:** O sistema segue um ciclo rigoroso: escreve testes -> escreve código -> executa testes. Se um teste falhar, ele tenta depurar o código automaticamente.
- **Feedback em Tempo Real:** A comunicação via **WebSockets** fornece um streaming de logs diretamente na interface do VS Code, permitindo que você acompanhe cada passo do processo.
- **Integração com o VS Code:** Opera como uma extensão do VS Code, lendo o contexto do seu workspace e fornecendo uma interface de chat para interação.
- **Extensível e Configurável:** A arquitetura permite adicionar novos agentes, dar-lhes novas ferramentas ou trocar o modelo de LLM subjacente através de variáveis de ambiente.

---

## ⚙️ Stack de Desenvolvimento

| Área | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Backend** | **Python 3** | Linguagem principal para a lógica dos agentes. |
| | **Flask & Flask-SocketIO** | Para criar o servidor WebSocket que permite a comunicação em tempo real. |
| | **CrewAI** | Framework para orquestrar os agentes de IA colaborativos. |
| | **python-dotenv** | Para gerenciar variáveis de ambiente e chaves de API. |
| **Frontend** | **Visual Studio Code API** | Para integrar a funcionalidade diretamente no editor. |
| | **TypeScript** | Linguagem para desenvolver a extensão do VS Code. |
| | **Socket.io-client** | Para conectar a extensão ao servidor WebSocket do backend. |

---

## 🧠 Lógica da Aplicação (Arquitetura)

O sistema é dividido em duas partes principais: a extensão do VS Code (frontend) e o servidor de agentes (backend).

1.  **Início (VS Code):** O usuário abre um projeto no VS Code e inicia o chat do Auto-Coder. A extensão estabelece uma conexão WebSocket com o servidor backend.
2.  **Envio do Prompt:** O usuário digita uma solicitação (ex: "Adicione uma função para validar CPF"). A extensão envia o prompt e o caminho do diretório do projeto para o backend via WebSocket.
3.  **Orquestração (Backend):** O servidor recebe o pedido e inicia o processo da equipe de agentes em uma thread de fundo:
    a. **Fase 1: Planejamento:** O **Gerente de Projetos** usa suas ferramentas para listar e ler os arquivos do projeto. Ele cria um plano detalhado, como: "Vou modificar o arquivo `validadores.py` para adicionar a função `validar_cpf` e criar um novo arquivo de teste `test_validadores.py`".
    b. **Fase 2: Teste (TDD):** O **Engenheiro de QA** recebe o plano e escreve o código para o `test_validadores.py`, definindo como a função `validar_cpf` deve se comportar.
    c. **Fase 3: Desenvolvimento e Depuração:**
        - O **Desenvolvedor Sênior** escreve a função `validar_cpf` no arquivo `validadores.py` com o objetivo de passar nos testes.
        - O **Engenheiro de QA** executa os testes.
        - **Se falhar**, o erro é enviado de volta ao Desenvolvedor, que tenta corrigir o código. Este ciclo se repete até 3 vezes.
    d. **Fase 4: Refatoração:** Após a aprovação nos testes, o **Especialista em Refatoração** analisa o código da nova função e o aprimora, focando em clareza, eficiência e boas práticas.
4.  **Feedback Contínuo:** Durante todas as fases, o backend envia mensagens de log via WebSocket, que são exibidas em tempo real na interface do chat no VS Code.
5.  **Conclusão:** Ao final do processo, uma mensagem de sucesso ou falha é enviada, e os arquivos no workspace do usuário estão modificados/criados.

---

## 🚀 Como Começar

### Pré-requisitos
- Node.js e npm
- Python 3.8+
- Uma chave de API de um provedor de LLM (ex: OpenAI)

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <NOME_DO_SEU_PROJETO>
    ```

2.  **Configure o Backend:**
    ```bash
    # Crie e ative um ambiente virtual
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate

    # Instale as dependências do Python
    pip install -r requirements.txt

    # Crie o arquivo de ambiente
    cp .env.example .env 
    ```
    - **Edite o arquivo `.env`** e adicione sua chave de API (ex: `OPENAI_API_KEY="sk-..."`).

3.  **Configure o Frontend:**
    ```bash
    # Instale as dependências do Node.js
    npm install
    ```

### Execução

1.  **Inicie o Backend:** Em um terminal, execute o servidor:
    ```bash
    python api.py
    ```

2.  **Inicie a Extensão:**
    - Abra o projeto no VS Code.
    - Pressione `F5` para iniciar o "Host de Desenvolvimento de Extensão".
    - Uma nova janela do VS Code será aberta.

3.  **Use o Agente:**
    - Na nova janela, abra a pasta do projeto que você deseja que o agente modifique.
    - Abra a paleta de comandos (`Ctrl+Shift+P`).
    - Execute o comando `Auto Coder: Start Chat`.
    - Envie suas instruções para a equipe de agentes!

---

## 💡 Sugestões e Próximos Passos (Roadmap)

Este projeto é uma base poderosa. Aqui estão algumas sugestões para melhorias futuras:

- **Contexto Avançado com Embeddings:** Em vez de apenas ler arquivos, usar uma base de dados vetorial (ex: ChromaDB) para realizar buscas semânticas no código, permitindo que os agentes encontrem funções e lógicas relevantes de forma muito mais eficaz.
- **Geração e Aplicação de Diffs:** Em vez de sobrescrever arquivos inteiros, o agente poderia gerar um `diff` da mudança proposta. A extensão do VS Code poderia então exibi-lo para que o usuário aprove ou rejeite a alteração, tornando o processo mais seguro.
- **Interação e Perguntas:** Permitir que os agentes façam perguntas de esclarecimento ao usuário através do chat quando um requisito não estiver claro, em vez de apenas prosseguir com uma suposição.
- **Seleção Dinâmica de Agentes:** Criar uma lógica no Gerente de Projetos para recrutar diferentes tipos de agentes para a equipe com base na tarefa (ex: recrutar um "Agente de Banco de Dados" se o prompt mencionar SQL).
- **Interface Gráfica para Configuração:** Criar uma interface no VS Code para configurar os agentes, suas personas e as chaves de API, em vez de editar arquivos de texto.
