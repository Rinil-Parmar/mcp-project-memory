from pathlib import Path

from src.adapters.transport.stdio_server import create_server


def test_server_exposes_phase_one_tools_and_resume_prompt(tmp_path: Path) -> None:
    server = create_server(tmp_path / "memory.sqlite3")

    tools = server._tool_manager.list_tools()
    prompts = server._prompt_manager.list_prompts()

    assert {tool.name for tool in tools} == {"record", "search", "get", "update_status"}
    assert {prompt.name for prompt in prompts} == {"resume"}


def test_mcp_record_search_and_resume_flow(tmp_path: Path) -> None:
    server = create_server(tmp_path / "memory.sqlite3")
    tools = {tool.name: tool.fn for tool in server._tool_manager.list_tools()}
    prompts = {prompt.name: prompt.fn for prompt in server._prompt_manager.list_prompts()}

    recorded = tools["record"](
        project="memory-project",
        type="decision",
        title="Use SQLite",
        summary="SQLite provides local persistence.",
        body="Use SQLite with FTS5 for version 0.1.",
        author="user",
        source_session="session-001",
        source_quote="Use SQLite for the MVP.",
    )
    searched = tools["search"](project="memory-project", query="SQLite")
    resumed = prompts["resume"](project="memory-project")

    assert recorded["item"]["status"] == "active"
    assert len(searched["hits"]) == 1
    assert "Use SQLite" in resumed
