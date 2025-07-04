import os
from flask import Flask, request
from flask_socketio import SocketIO
from gerador_de_agentes import CrewGenerator
from crewai import Task, Crew

app = Flask(__name__)
# Chave secreta para a sessão do Flask, necessária para o SocketIO
app.config['SECRET_KEY'] = 'secret!very-secret-key' 
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------------------------
# Endpoint REST para auto-complete em linha
# ---------------------------------------------


@app.post('/inline_completion')
def inline_completion():
    """Gera uma sugestão de código simples baseada no prefixo enviado.

    Este endpoint é utilizado pela extensão do VS Code para oferecer
    sugestões estilo GitHub Copilot. Por padrão, utiliza a API OpenAI
    se a variável de ambiente OPENAI_API_KEY estiver definida.
    Caso contrário, retorna uma string vazia.
    """
    try:
        data = request.get_json(force=True)
        prefix: str = data.get('prefix', '')  # type: ignore[arg-type]
        language: str = data.get('language', 'python')  # type: ignore[arg-type]

        # Se estiver vazio ou muito curto, evita chamadas desnecessárias
        if len(prefix.strip()) < 3:
            return {"completion": ""}, 200

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            # Chave não configurada, retorna vazio para evitar falhas
            return {"completion": ""}, 200

        import openai  # import local para não exigir a lib em todos os ambientes

        openai.api_key = api_key

        # Solicita continuação concisa do código
        response = openai.ChatCompletion.create(  # type: ignore[attr-defined]
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert {language} coding assistant. "
                        "Continue the user's code snippet only with the next logical tokens. "
                        "Do NOT add any commentary or markdown formatting."
                    ).format(language=language),
                },
                {"role": "user", "content": prefix},
            ],
            max_tokens=64,
            temperature=0.2,
            n=1,
            stop=None,
        )

        completion = response.choices[0].message["content"].lstrip("\n")
        return {"completion": completion}, 200

    except Exception:
        # Em caso de erro, evita travar a extensão
        return {"completion": ""}, 200

MAX_DEBUG_ATTEMPTS = 3

def run_crew_process(sid, user_prompt, project_dir):
    """Esta função contém a lógica principal da equipe e emite logs via WebSocket."""
    
    def log(message):
        """Função auxiliar para emitir logs para um cliente específico."""
        socketio.emit('log_message', {'data': message}, room=sid)  # type: ignore[arg-type]
        # Pequena pausa para garantir que a mensagem seja enviada
        socketio.sleep(0.1)  # type: ignore[attr-defined]

    try:
        log(f"Iniciando equipe no diretório: {os.path.abspath(project_dir)}")

        generator = CrewGenerator(project_dir=project_dir)
        crew_config = generator.get_coding_crew()
        agents = crew_config["agents"]

        # --- Fase 1: Planejamento ---
        log("Fase 1: O Gerente de Projetos está analisando o projeto e planejando as tarefas...")
        plan_task = Task(
            description=f"""Analisar o pedido do usuário: '{user_prompt}' no contexto do diretório '{os.path.abspath(project_dir)}'. 
            Use a ferramenta `read_directory` para entender a estrutura de arquivos. 
            Crie um plano detalhado, especificando arquivos a serem criados/modificados.""",
            expected_output="Um plano claro e detalhado.",
            agent=agents["manager"]
        )
        planning_crew = Crew(agents=[agents["manager"]], tasks=[plan_task])
        plan_result = planning_crew.kickoff()
        log(f"Plano recebido: {plan_result}")

        # (A lógica de parsing de nome de arquivo e as fases 2, 3, 4 permanecem as mesmas)
        # ...
        # --- Fase 2: Desenvolvimento ---
        log("Fase 2: O Desenvolvedor está implementando o código conforme o plano...")
        developer_task = Task(
            description=f"""Implemente as alterações e/ou novos arquivos descritos no seguinte plano:\n\n{plan_result}\n\nGaranta que o código esteja organizado, bem documentado e siga as melhores práticas de Python.""",
            expected_output="Código implementado ou modificado conforme o plano.",
            agent=agents["developer"]
        )
        developer_crew = Crew(agents=[agents["developer"]], tasks=[developer_task])
        dev_result = developer_crew.kickoff()
        log(f"Resultado do desenvolvimento: {dev_result}")

        # --- Fase 3: QA ---
        log("Fase 3: O Engenheiro de QA está escrevendo e executando testes...")
        qa_task = Task(
            description=f"""Com base no plano a seguir e no código atual do projeto, escreva testes unitários com pytest para validar a nova funcionalidade e execute-os.\n\nPlano:\n{plan_result}\n\nSe os testes falharem, descreva as falhas.""",
            expected_output="Todos os testes passaram ou foram listadas as falhas encontradas.",
            agent=agents["qa"]
        )
        qa_crew = Crew(agents=[agents["qa"]], tasks=[qa_task])
        qa_result = qa_crew.kickoff()
        log(f"Resultado do QA: {qa_result}")

        # --- Fase 4: Refatoração ---
        log("Fase 4: O Especialista em Refatoração está melhorando o código...")
        refactor_task = Task(
            description="""Analise o código atualizado no projeto e refatore-o para melhorar clareza, eficiência e aderência às boas práticas de Python. Não altere a lógica de negócios.""",
            expected_output="Código refatorado e otimizado.",
            agent=agents["refactorer"]
        )
        refactor_crew = Crew(agents=[agents["refactorer"]], tasks=[refactor_task])
        refactor_result = refactor_crew.kickoff()
        log(f"Resultado da refatoração: {refactor_result}")

        final_result = f"{plan_result}\n\n----\n{dev_result}\n\n----\n{qa_result}\n\n----\n{refactor_result}"

        log("PROJETO CONCLUÍDO COM SUCESSO!")
        socketio.emit('crew_finished', {'status': 'success', 'result': final_result}, room=sid)  # type: ignore[arg-type]

    except Exception as e:
        log(f"ERRO: {str(e)}")
        socketio.emit('crew_finished', {'status': 'error', 'result': str(e)}, room=sid)  # type: ignore[arg-type]

@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")

@socketio.on('start_crew')
def handle_start_crew(data):
    user_prompt = data.get('prompt', '')
    project_dir = data.get('project_dir', '.')
    
    # Inicia o processo da equipe em uma thread de fundo para não bloquear o servidor
    socketio.start_background_task(run_crew_process, request.sid, user_prompt, project_dir)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}")

if __name__ == '__main__':
    # O `debug=True` do Flask não é compatível com o modo de produção do SocketIO
    # Use `socketio.run(app, debug=True)` para desenvolvimento
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)