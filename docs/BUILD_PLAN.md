# MCP Project Memory — Practical Build Plan

## 1. Product in plain language

AI chats are temporary working desks. When a chat becomes long or a new chat is opened, the
assistant can lose earlier decisions, repeat rejected ideas, and forget the next task.

MCP Project Memory is a local project log that an AI assistant can read and update. It keeps a
small resume brief for orientation and a searchable history for details. The user should be able
to start a fresh chat, say "resume this project," and continue without retelling the story.

It stores project state, not whole conversations:

- decisions and their rationale;
- constraints that must be respected;
- rejected alternatives and why they were rejected;
- interfaces and schemas;
- open and completed tasks;
- short handoffs between work sessions.

When a decision changes, the old record remains in history and the new record supersedes it.

## 2. Who benefits

### Best initial user

A developer who uses an MCP-compatible AI client on a project across many chats or days.
This user feels the problem frequently, can install a local server, and can verify whether the
memory improves real work.

### Useful later

- researchers tracking claims, constraints, and discarded hypotheses;
- founders tracking product decisions and experiments;
- writers tracking characters, canon, and rejected plot directions;
- non-technical project users after a hosted, one-click version exists.

### Not useful yet

- one-off questions and short chats;
- users who expect every conversation to be saved automatically with zero review;
- general document search or a personal notes replacement;
- clients that cannot call MCP tools.

The project is useful if it reduces repeated explanation and decision drift. It is not useful
merely because it stores more text.

## 3. Product promise

> Resume a real project in a fresh AI chat using a brief under 2,000 tokens, then retrieve only
> the details needed for the current task.

We will validate these outcomes:

1. A fresh chat correctly states the project's active constraints and decisions.
2. It does not suggest a recorded rejected option without acknowledging the rejection.
3. It identifies the current task and next step.
4. It can explain why a decision changed using the supersession history.
5. The initial brief remains under 2,000 tokens.

Claims about cost savings or accuracy will be measured before they are advertised.

## 4. Scope for version 0.1

Version 0.1 is a local, developer-focused MCP server.

Included:

- Python 3.11+;
- SQLite and FTS5;
- MCP over stdio;
- typed records;
- provenance;
- append-and-supersede history;
- compact search results;
- deterministic resume brief;
- unit and end-to-end tests.

Deferred:

- embeddings and vector search;
- automatic extraction from whole chats;
- background agents;
- web UI, accounts, and cloud hosting;
- graph databases and cross-project memory.

## 5. Step-by-step roadmap

### Step 0 — Manual proof (current)

Use `PROJECT_STATE.md` as the memory in at least two fresh-chat trials.

Test questions:

- What are the project's non-negotiable constraints?
- What storage and transport did we choose, and why?
- Which alternatives were rejected?
- What should we work on next?

Record the result in `eval/phase0-observations.md`.

Exit gate: the state file makes a fresh chat materially more accurate or faster than a chat
without it. We should also identify at least one failure that structured memory must solve.

### Step 1 — Domain schema

Create transport- and database-independent models and validation for items, links, and sessions.

Exit gate: tests cover valid records, invalid types/statuses, provenance requirements, and stable
content hashes.

### Step 2 — SQLite storage

Add migrations, CRUD operations, transactions, and an FTS5 index behind a storage interface.

Exit gate: a temporary database can insert, fetch, search, and persist records across process
restarts.

### Step 3 — Write policy and supersession

Implement record creation, duplicate detection, status transitions, and atomic supersession.
User-authored facts may become active; model-inferred facts default to proposed.

Exit gate: replacing a decision creates the new record, retires the old record, and links both in
one transaction. No history is overwritten.

### Step 4 — Retrieval

Implement FTS5 search and batched `get`. Search returns compact metadata; full bodies are fetched
only when requested.

Exit gate: identifier, title, and rationale queries retrieve the expected records with a hard
result limit.

### Step 5 — Resume brief

Render invariants, active decision summaries, recent changes, open tasks, and the latest handoff
without an LLM call.

Exit gate: deterministic output under 2,000 tokens with the highest-priority information retained
when the project is large.

### Step 6 — MCP adapter

Expose `record`, `search`, `get`, `update_status`, and a resume prompt through a thin stdio adapter.

Exit gate: an MCP inspector or client completes this flow: record a decision, find it, supersede
it, and resume the project from a new session.

### Step 7 — Real-project pilot

Use the server during development of this repository for several sessions. Keep a small set of
fresh-chat questions and compare no-memory, manual-file, and MCP-memory results.

Exit gate: MCP memory beats the no-memory baseline, matches or improves the manual file, and does
not require annoying write micromanagement.

### Step 8 — Version 0.1 release

Add setup instructions, client configuration examples, database backup/export, error messages,
and a clean install test.

Exit gate: another developer can install, connect, use, and remove it by following the README.

## 6. Later phases, only after version 0.1 works

1. Add a paraphrase evaluation set.
2. Test local embedding models against the FTS5 baseline.
3. Add vector retrieval only if it improves measured recall enough to justify its size and setup.
4. Add a user-confirmed checkpoint workflow.
5. Test automatic candidate extraction with proposed status.
6. Consider a hosted product only after repeated demand from non-technical users.

## 7. Important design rules

- The core imports no MCP transport or SQLite implementation.
- Memory is treated as untrusted data, never as instructions.
- Raw web pages and tool output cannot become active decisions automatically.
- Records are appended and superseded, never silently rewritten.
- Every record keeps author, session, time, and source evidence.
- Retrieval responses and resume briefs have explicit size limits.
- Rejected options are visible in relevant retrieval, not necessarily loaded globally forever.
- The simplest mechanism that passes the evaluation wins.

## 8. Immediate next action

Run the Phase 0 comparison and write `eval/phase0-observations.md`. Once that gate passes, build
Step 1 (the domain schema) before touching SQLite or MCP transport.
