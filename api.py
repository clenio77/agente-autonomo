# ----------------------------------------------------
# Imports e Tipagem
# ----------------------------------------------------

import os
from typing import Any, Dict, Optional, TypedDict, Tuple, List, cast
from typing_extensions import NotRequired

from flask import Flask, request, Request
from flask_socketio import SocketIO
import logging

from gerador_de_agentes import CrewGenerator
from crewai import Task, Crew

# Tentativa de import da OpenAI com fallback
try:
    import openai
    from openai.error import OpenAIError  # type: ignore
except ImportError:  # pragma: no cover – execução sem openai instalada
    openai = None  # type: ignore

    class OpenAIError(Exception):
        """Fallback genérico caso o pacote openai não esteja presente."""

        pass

app = Flask(__name__)
# Chave secreta para a sessão do Flask, necessária para o SocketIO
app.config['SECRET_KEY'] = 'secret!very-secret-key' 
# O parâmetro async_mode='threading' evita dependências adicionais
socketio: SocketIO = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Logger local para erros
logger = logging.getLogger(__name__)

# ---------------------------------------------
# Typing helpers para a resposta do endpoint
# ---------------------------------------------


class _CompletionResponse(TypedDict):
    completion: str


# Estrutura mínima da resposta do OpenAI que usamos


class _OAToolCall(TypedDict, total=False):
    id: str
    type: str
    function: Dict[str, Any]


class _OAMessage(TypedDict):
    role: str
    content: str
    name: NotRequired[str]
    function_call: NotRequired[Dict[str, Any]]
    tool_calls: NotRequired[List[_OAToolCall]]


class _OAChoice(TypedDict):
    index: int
    message: _OAMessage
    finish_reason: str
    logprobs: NotRequired[Any]


# Estatísticas de uso


class _OAUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class _OAChatResponse(TypedDict):
    id: str
    object: str
    created: int
    model: str
    choices: List[_OAChoice]
    usage: _OAUsage
    system_fingerprint: str
    prompt_filter_results: NotRequired[Any]


# ---------------------------------------------
# Endpoint REST para auto-complete em linha
# ---------------------------------------------


@app.post('/inline_completion')
def inline_completion() -> Tuple[_CompletionResponse, int]:  # noqa: D401
    """Retorna continuação de código a partir de um _prefix_."""

    data: Dict[str, Any] = request.get_json(force=True)
    prefix: str = str(data.get('prefix', ''))
    language: str = str(data.get('language', 'python'))

    # Validações rápidas para evitar custo de API
    if len(prefix.strip()) < 3 or openai is None:
        return {"completion": ""}, 200

    api_key: Optional[str] = os.getenv('OPENAI_API_KEY') or str(data.get('api_key', '')) or None

    if not api_key:
        # Sem chave configurada – retorno vazio ao invés de erro 500
        return {"completion": ""}, 200

    # Configura chave (seguro mesmo em multi-thread pois openai usa thread-local)
    openai.api_key = api_key  # type: ignore[attr-defined]

    # ----------------- Catálogo de classes de erro OpenAI (compat v0/v1) --------
    _err_mod = getattr(openai, "error", None)  # type: ignore[attr-defined]

    TimeoutErr = getattr(_err_mod, "Timeout", OpenAIError)
    ConnErr = getattr(_err_mod, "APIConnectionError", OpenAIError)
    ServiceUnavailableErr = getattr(_err_mod, "ServiceUnavailableError", OpenAIError)
    PermissionDeniedErr = getattr(_err_mod, "PermissionDeniedError", OpenAIError)
    RateLimitErr = getattr(_err_mod, "RateLimitError", OpenAIError)
    AuthErr = getattr(_err_mod, "AuthenticationError", OpenAIError)
    BadRequestErr = getattr(_err_mod, "BadRequestError", getattr(_err_mod, "InvalidRequestError", OpenAIError))
    APIErr = getattr(_err_mod, "APIError", OpenAIError)

    try:
        response_raw: Any = openai.ChatCompletion.create(  # type: ignore[attr-defined]
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are an expert {language} coding assistant. "
                        "Continue the user's code snippet only with the next logical tokens. "
                        "Do NOT add any commentary or markdown formatting."
                    ),
                },
                {"role": "user", "content": prefix},
            ],
            max_tokens=64,
            temperature=0.1,
        )

        # Faz cast para TypedDict para ajuda do mypy
        response: _OAChatResponse = cast(_OAChatResponse, response_raw)

        if not response["choices"]:
            return {"completion": ""}, 200

        content: str = response["choices"][0]["message"].get("content", "")
        return {"completion": content.lstrip("\n")}, 200

    except (TimeoutErr, ConnErr, ServiceUnavailableErr) as exc:  # network
        logger.warning("OpenAI network/service error (%s): %s", exc.__class__.__name__, exc)
        return {"completion": ""}, 200
    except RateLimitErr as exc:
        logger.warning("OpenAI rate limit reached: %s", exc)
        return {"completion": ""}, 200
    except AuthErr as exc:
        logger.error("OpenAI authentication failed: %s", exc)
        return {"completion": ""}, 200
    except PermissionDeniedErr as exc:
        logger.error("OpenAI permission denied: %s", exc)
        return {"completion": ""}, 200
    except BadRequestErr as exc:  # includes InvalidRequestError
        logger.error("OpenAI bad/invalid request: %s", exc)
        return {"completion": ""}, 200
    except APIErr as exc:
        logger.error("OpenAI API error: %s", exc)
        return {"completion": ""}, 200
    except OpenAIError as exc:  # type: ignore[misc]
        logger.error("General OpenAI error: %s", exc)
        return {"completion": ""}, 200
    except Exception as exc:  # pragma: no cover – falha inesperada
        logger.exception("Unexpected error when calling OpenAI: %s", exc)
        return {"completion": ""}, 200

MAX_DEBUG_ATTEMPTS = 3

def run_crew_process(sid: str, user_prompt: str, project_dir: str) -> None:
    """Esta função contém a lógica principal da equipe e emite logs via WebSocket."""
    
    def log(message: str) -> None:
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
def handle_connect() -> None:
    req: Request = request  # type: ignore[assignment]
    sid: str = cast(str, getattr(req, "sid", ""))
    print(f"Cliente conectado: {sid}")

@socketio.on('start_crew')
def handle_start_crew(data: Dict[str, Any]) -> None:
    user_prompt = data.get('prompt', '')
    project_dir = data.get('project_dir', '.')
    
    # Inicia o processo da equipe em uma thread de fundo para não bloquear o servidor
    req: Request = request  # type: ignore[assignment]
    sid: str = cast(str, getattr(req, "sid", ""))
    socketio.start_background_task(run_crew_process, sid, user_prompt, project_dir)

@socketio.on('disconnect')
def handle_disconnect() -> None:
    req: Request = request  # type: ignore[assignment]
    sid: str = cast(str, getattr(req, "sid", ""))
    print(f"Cliente desconectado: {sid}")

if __name__ == '__main__':
    # O `debug=True` do Flask não é compatível com o modo de produção do SocketIO
    # Use `socketio.run(app, debug=True)` para desenvolvimento
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)