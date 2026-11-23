# 🧠 MCP Project Memory

**Persistent project memory for AI assistants — resume any project at full depth from a fresh chat.**

## What is this?

A local MCP (Model Context Protocol) server that gives AI assistants like Claude, Cursor, and others a persistent memory layer for long-running projects. Instead of pasting 50k tokens of context into every new chat, the AI reads a ~2k token brief and can search for details on demand.

## Key Features

- **Resume Brief** — Auto-generated 1-page project summary (≤2k tokens)
- **Typed Records** — Decisions, constraints, rejected ideas, interfaces, tasks, episodes
- **Supersession** — Decisions evolve with full history (never overwrite, always archive)
- **Rejected Ideas** — Prevents AI from re-proposing killed options
- **Provenance** — Every record has: who said it, when, in what session, the original quote
- **Hybrid Search** — FTS5 keyword + vector semantic search (Phase 2)
- **100% Local** — SQLite on your machine, no cloud, no accounts

## Quick Start

```powershell
# Create an isolated environment and install development dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run over stdio (normally an MCP client starts this process)
.\.venv\Scripts\python.exe server.py --database .memory\project-memory.sqlite3

# Verify the implementation
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .

# Exercise record, search, supersession, and resume against real SQLite
.\.venv\Scripts\python.exe scripts\validate_flow.py
```

Example MCP client configuration on Windows:

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "D:\\Project\\mcp-project-memory\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\Project\\mcp-project-memory\\server.py",
        "--database",
        "D:\\Project\\mcp-project-memory\\.memory\\project-memory.sqlite3"
      ]
    }
  }
}
```

The server exposes four tools—`record`, `search`, `get`, and `update_status`—plus the `resume`
prompt. User-sourced records become active immediately; model-inferred records stay proposed until
confirmed.

For the component boundaries, database layout, security rules, and complete request flows, read
the [technical overview](docs/TECHNICAL_OVERVIEW.md).

## Architecture

```
Claude Desktop ──stdio──▶ MCP Server ──▶ SQLite (single file)
```

The core is transport-agnostic and storage-agnostic (hexagonal architecture). Moving from local stdio to hosted HTTP is an adapter swap, not a rewrite.

## Status

🚧 Phase 1 — Core MVP integration (in progress)

The schema, SQLite/FTS5 adapter, write policy, supersession, retrieval, bounded resume brief, and
MCP stdio adapter are implemented. The next gate is a real-client pilot. See the
[practical build plan](docs/BUILD_PLAN.md) and record manual comparison evidence in
[`eval/phase0-observations.md`](eval/phase0-observations.md).
