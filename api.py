import os
import time
from flask import Flask, request
from flask_socketio import SocketIO, emit
from gerador_de_agentes import CrewGenerator
from crewai import Task, Crew

app = Flask(__name__)
# Chave secreta para a sessão do Flask, necessária para o SocketIO
app.config['SECRET_KEY'] = 'secret!very-secret-key' 
socketio = SocketIO(app, cors_allowed_origins="*")

MAX_DEBUG_ATTEMPTS = 3

def run_crew_process(sid, user_prompt, project_dir):
    """Esta função contém a lógica principal da equipe e emite logs via WebSocket."""
    
    def log(message):
        """Função auxiliar para emitir logs para um cliente específico."""
        socketio.emit('log_message', {'data': message}, room=sid)
        # Pequena pausa para garantir que a mensagem seja enviada
        socketio.sleep(0.1) 

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

        log("PROJETO CONCLUÍDO COM SUCESSO!")
        socketio.emit('crew_finished', {'status': 'success', 'result': plan_result}, room=sid)

    except Exception as e:
        log(f"ERRO: {str(e)}")
        socketio.emit('crew_finished', {'status': 'error', 'result': str(e)}, room=sid)

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