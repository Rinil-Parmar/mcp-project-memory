# MCP Project Memory — Technical Overview

## What has been built

The current version is a local MCP server backed by SQLite. It gives an AI client four typed tools
and one resume prompt while keeping the domain logic independent from both MCP and SQLite.

The important distinction is that this is a project-state ledger, not a transcript archive. It
stores durable facts that future work must respect and leaves temporary conversation text behind.

## Components and connections

```text
AI client (Claude, Cursor, another MCP host)
        |
        | MCP JSON-RPC over stdio
        v
stdio_server.py
        |
        +--> MemoryRepository ---- write policy and supersession
        +--> MemoryRetrieval ----- compact search and full record fetch
        +--> BriefRenderer ------- deterministic resume summary
                    |
                    v
              MemoryStore port
                    |
                    v
              SQLiteStore
                    |
        +-----------+-----------+
        |           |           |
      items       links       sessions
        |
     items_fts (FTS5 keyword index)
```

### Domain layer

`src/core/schema.py` defines the records and invariants:

- `MemoryItem`: a decision, constraint, rejection, interface, schema, task, or episode;
- `MemoryLink`: a typed relationship such as `supersedes`;
- `MemorySession`: a work session and its final handoff;
- enums for record type, status, author, and link relationship;
- timezone validation, UUID validation, priority bounds, and stable SHA-256 content hashes.

The content hash covers semantic content but excludes record ID and timestamps. Two records with
the same project, type, title, summary, body, and scope are therefore detected as duplicates even
if they were submitted at different times.

### Storage boundary

`src/core/ports.py` defines the `MemoryStore` protocol. Core services know this interface but do
not import SQLite. `src/adapters/storage/sqlite_store.py` implements the interface.

This is the hexagonal or ports-and-adapters boundary. A future PostgreSQL adapter can implement
the same operations without rewriting record policy, retrieval, or brief rendering.

### SQLite layout

- `items` stores typed, versioned records and provenance.
- `links` stores relationships between records.
- `sessions` stores session goals and handoffs.
- `items_fts` is an FTS5 full-text index over title, summary, body, and scope.

`UNIQUE(project, content_hash)` enforces semantic deduplication at the database level. Foreign keys
prevent links to records that do not exist. Supersession updates the old record, inserts the new
record, and creates the link inside one transaction, so a partial replacement cannot be committed.

### Write policy

`src/core/repository.py` owns the rules for writes:

1. User-sourced records start as `active`.
2. Model-inferred records start as `proposed`.
3. A model-authored proposal cannot supersede an active fact until a user confirms it.
4. Exact semantic duplicates return the existing record rather than creating another row.
5. Supersession is append-only: the old record becomes `superseded`; it is not deleted.
6. Status changes must follow an allowed transition.

These rules reduce memory poisoning and stop repeated entries from turning the store into an
unstructured transcript.

### Retrieval

`src/core/retrieval.py` exposes two levels:

- `search` returns compact metadata rows, limited to eight by default;
- `get` loads full bodies for selected IDs, limited to twenty records per call.

The SQLite adapter converts normal user text into a safe FTS5 `AND` query and filters by project
and status. The index deliberately treats sentence punctuation differently from identifier
characters so words at the end of a sentence remain searchable.

### Resume brief

`src/core/brief.py` builds the brief without an LLM call. It orders:

1. invariants and constraints;
2. active decisions;
3. rejected alternatives;
4. open tasks;
5. recently superseded decisions;
6. the latest handoff.

The renderer uses a conservative three-characters-per-token allowance and truncates at 6,000
characters for the default 2,000-token budget. It also labels memory as project data rather than
instructions, which helps prevent stored prompt injection from gaining system-level authority.

## End-to-end flows

### Recording a decision

```text
AI calls record
  -> MCP validates tool arguments
  -> repository assigns active/proposed authority
  -> schema validates the record and calculates its hash
  -> repository checks for a duplicate
  -> SQLite inserts item and FTS row in one transaction
  -> tool returns the stored typed record
```

### Replacing an earlier decision

```text
AI calls record(..., supersedes=old_id)
  -> repository requires a user-authorized active replacement
  -> SQLite verifies same project and same record type
  -> old item becomes superseded with valid_to and retired_at
  -> new item is inserted
  -> new --supersedes--> old link is inserted
  -> transaction commits all three changes together
```

### Starting a fresh chat

```text
User asks to resume project
  -> AI requests the resume prompt
  -> BriefRenderer queries active/proposed/recent records
  -> client receives a bounded orientation brief
  -> AI calls search when the current task needs more detail
  -> AI calls get only for the relevant record IDs
```

This is the three-tier context strategy: small brief first, scoped search second, full bodies last.

## Exposed MCP surface

- `record`: store typed durable project state and optionally supersede an earlier record;
- `search`: retrieve compact keyword matches;
- `get`: fetch full records by ID;
- `update_status`: confirm proposals or finish/reject active records;
- `resume`: render the bounded fresh-chat brief.

Tool descriptions tell the model when it must not write: exploration, speculation, raw web data,
and raw tool output are excluded.

## Verification completed

- schema and validation tests;
- stable hashing and duplicate tests;
- persistence across SQLite process restarts;
- FTS5 title/body search and project isolation;
- atomic supersession and rollback on failure;
- authority and status-transition tests;
- resume composition and size-cap tests;
- MCP tool registration and tool-flow tests;
- repeatable real-SQLite validation through `scripts/validate_flow.py`.

The remaining external gate is to add the server configuration to one real MCP client and observe
the full JSON-RPC stdio handshake in that client.
