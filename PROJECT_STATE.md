# MCP Project Memory — Project State (Phase 1)
# This file remains the human-readable bootstrap until the real-client pilot seeds the database.

## Invariants (never change without explicit override)
- Transport-agnostic core: NO transport or DB imports in core/
- Append-and-supersede: NEVER overwrite a record, always archive + link
- Provenance on every row: author, session, source quote
- /resume brief ≤ 2,000 tokens
- Local-first: SQLite, stdio, no cloud dependency

## Active Decisions
- Storage: SQLite + FTS5 (single file, local)
- Transport: MCP over stdio
- Language: Python 3.11+
- MCP SDK: FastMCP from mcp 1.x (pinned below 2.0 for the stable FastMCP API)
- Schema: Typed records with bi-temporal tracking
- Architecture: Hexagonal (ports & adapters)

## Rejected Alternatives
- ❌ Neo4j / graph DB — overkill for Phase 1, revisit only on measured multi-hop failure
- ❌ Full RAG pipeline — we're not building a document search, we're building a decision ledger
- ❌ Mem0 — designed for user preferences, not project state
- ❌ In-place record rewrites — LLM rewrites corrupt data over time

## Open Tasks
- [ ] Phase 0: Complete the comparison in eval/phase0-observations.md
- [x] Phase 1 foundation: schema, SQLite/FTS5, write policy, retrieval, brief, MCP adapter
- [x] Phase 1 core integration: record/search/supersede/resume against a real SQLite file
- [ ] Phase 1 integration: test with an MCP client and complete the real-project pilot

## Current Handoff
- Build plan is documented in docs/BUILD_PLAN.md.
- Core MVP foundation is implemented with automated tests.
- Technical flow is documented in docs/TECHNICAL_OVERVIEW.md.
- scripts/validate_flow.py validates the complete core flow with a real SQLite database.
- Next action: connect an MCP client and run the end-to-end record/search/supersede/resume flow.
- Note: async stdio could not be exercised inside the current execution host because even a
  minimal asyncio event loop hangs there; MCP registration and tool flows are covered synchronously.

## Current Phase
Phase 1 — MCP Client Integration
