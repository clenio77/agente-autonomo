import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai_tools import FileWriteTool, CodeExecutionTool, FileReadTool, DirectoryReadTool, SerperDevTool # Adicionadas novas ferramentas

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class CrewGenerator:
    def __init__(self, project_dir='.'): # O padrão agora é o diretório atual
        self.project_dir = project_dir
        self.file_write_tool = FileWriteTool(root_dir=self.project_dir)
        self.file_read_tool = FileReadTool(root_dir=self.project_dir)
        self.code_execution_tool = CodeExecutionTool(working_directory=self.project_dir)
        self.directory_read_tool = DirectoryReadTool(directory=self.project_dir)
        self.search_tool = SerperDevTool()
        self.llm_config = self._get_llm_config()

    def _get_llm_config(self):
        if os.getenv("OPENAI_API_KEY"):
            print("Usando configuração da OpenAI.")
            return {"api_key": os.getenv("OPENAI_API_KEY")}
        if os.getenv("GEMINI_API_KEY"):
            print("Usando configuração do Google Gemini.")
            return {"provider": "google_gemini", "api_key": os.getenv("GEMINI_API_KEY")}
        print("Nenhuma chave de API encontrada. Usando configuração padrão do CrewAI.")
        return None

    def _create_agent(self, role, goal, backstory, tools, allow_delegation=False):
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            allow_delegation=allow_delegation,
            tools=tools,
            llm=self.llm_config if self.llm_config else None
        )
        return agent

    def get_coding_crew(self):
        # --- Definição dos Agentes da Equipe de Codificação ---
        project_manager = self._create_agent(
            role="Gerente de Projetos de Software com Consciência de Contexto",
            goal="Analisar um pedido de software no contexto de uma base de código existente. Identificar arquivos relevantes e criar um plano de desenvolvimento detalhado para modificar arquivos existentes ou criar novos.",
            backstory="Você é um gerente de projetos experiente que se destaca na compreensão de bases de código existentes. Você traduz requisitos de alto nível em tarefas acionáveis, especificando exatamente quais arquivos devem ser tocados.",
            tools=[self.directory_read_tool, self.file_read_tool, self.search_tool],
            allow_delegation=False
        )
        
        senior_developer = self._create_agent(
            role='Desenvolvedor de Software Sênior em Python',
            goal='Escrever, modificar ou corrigir código Python limpo e eficiente com base em um plano detalhado.',
            backstory="Você é um programador Python experiente que segue planos meticulosamente. Você é um especialista em ler, entender e modificar código existente, bem como em criar novas funcionalidades.",
            tools=[self.file_read_tool, self.file_write_tool, self.search_tool]
        )

        qa_agent = self._create_agent(
            role='Engenheiro de Garantia de Qualidade de Software',
            goal="Garantir a qualidade do código através da criação e execução de testes rigorosos, seja para novas funcionalidades ou para modificações em código existente.",
            backstory="Você é um engenheiro de QA meticuloso. Você cria e executa testes unitários com pytest para validar o código, garantindo que as novas alterações não quebrem a funcionalidade existente.",
            tools=[self.code_execution_tool, self.file_read_tool, self.file_write_tool]
        )

        refactoring_agent = self._create_agent(
            role="Especialista em Refatoração de Código",
            goal="Melhorar a qualidade de um código já funcional, focando em clareza, eficiência e adesão às melhores práticas.",
            backstory="Você é um arquiteto de software que transforma bom código em código excepcional. Você analisa o código que já passou nos testes e o aprimora.",
            tools=[self.file_read_tool, self.file_write_tool]
        )

        return {
            "agents": {
                "manager": project_manager,
                "developer": senior_developer,
                "qa": qa_agent,
                "refactorer": refactoring_agent
            }
        }