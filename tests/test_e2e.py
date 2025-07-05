import sys

# --- Criação de stubs para evitar dependências pesadas na importação ---
module_name = "crewai_tools"
if module_name not in sys.modules:
    import types

    stubs = types.ModuleType(module_name)

    class _StubTool:  # noqa: D401,E701
        def __init__(self, *args, **kwargs):
            pass

    # Atribui ferramentas esperadas como classes vazias
    for tool_name in [
        "FileWriteTool",
        "CodeExecutionTool",
        "FileReadTool",
        "DirectoryReadTool",
        "SerperDevTool",
    ]:
        setattr(stubs, tool_name, _StubTool)

    sys.modules[module_name] = stubs

# Agora podemos importar api com segurança
import api


def test_imports():
    """Certifica que os módulos principais podem ser importados."""
    import gerador_de_agentes  # noqa: F401
    assert api is not None


def test_run_crew_process_monkeypatched(monkeypatch, tmp_path):
    """Executa run_crew_process com dependências stubadas para evitar chamadas externas."""
    # Stub Task e Crew para evitar dependência do CrewAI
    class DummyTask:
        def __init__(self, *args, **kwargs):
            pass

    class DummyCrew:
        def __init__(self, *args, **kwargs):
            pass

        def kickoff(self):
            return "dummy result"

    monkeypatch.setattr(api, "Task", DummyTask)
    monkeypatch.setattr(api, "Crew", DummyCrew)

    # Stub CrewGenerator para retornar um conjunto mínimo de agentes
    class DummyAgent:
        def __init__(self, name):
            self.name = name

        def kickoff(self):
            return f"{self.name} done"

    class DummyCrewGenerator:
        def __init__(self, project_dir="."):
            pass

        def get_coding_crew(self):
            dummy = DummyAgent("agent")
            return {"agents": {"manager": dummy, "developer": dummy, "qa": dummy, "refactorer": dummy}}

    monkeypatch.setattr(api, "CrewGenerator", DummyCrewGenerator)

    # Capturar emissões do socketio
    emitted = []

    def fake_emit(event, data, room=None):  # noqa: ANN001
        emitted.append((event, data))

    monkeypatch.setattr(api.socketio, "emit", fake_emit)
    monkeypatch.setattr(api.socketio, "sleep", lambda x: None)

    # Executa o processo
    api.run_crew_process("sid123", "teste de prompt", tmp_path)

    # Verifica se houve pelo menos uma mensagem de finalização
    assert any(evt == "crew_finished" for evt, _ in emitted)