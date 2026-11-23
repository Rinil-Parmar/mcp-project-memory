"""Validate the complete core flow against a real SQLite database.

This exercises the same application services used by the MCP adapter without requiring an MCP
client. By default it uses a temporary database; pass --database to keep the result for inspection.
"""

from __future__ import annotations

import argparse
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory

from src.adapters.storage import SQLiteStore
from src.core.brief import BriefRenderer
from src.core.repository import MemoryRepository
from src.core.retrieval import MemoryRetrieval
from src.core.schema import Author, ItemStatus, ItemType, MemorySession


def validate(database: Path) -> str:
    project = "mcp-project-memory-validation"
    with SQLiteStore(database) as store:
        repository = MemoryRepository(store)
        retrieval = MemoryRetrieval(store)

        repository.record(
            project=project,
            item_type=ItemType.CONSTRAINT,
            title="Keep the first release local",
            summary="Version 0.1 must not require a cloud service.",
            body="Use a local SQLite database and MCP stdio transport.",
            author=Author.USER,
            source_session="validation-session",
            source_quote="Keep version 0.1 completely local.",
            priority=0,
        )
        repository.record(
            project=project,
            item_type=ItemType.REJECTED,
            title="Do not use Neo4j in version 0.1",
            summary="A graph database is unnecessary before measured multi-hop failures.",
            body="Revisit a graph database only if evaluation shows a real multi-hop limitation.",
            author=Author.USER,
            source_session="validation-session",
            source_quote="Neo4j is overkill for the MVP.",
        )
        original = repository.record(
            project=project,
            item_type=ItemType.DECISION,
            title="Use SQLite",
            summary="SQLite provides a single local database file.",
            body="Use SQLite with FTS5 for version 0.1 storage and keyword retrieval.",
            author=Author.USER,
            source_session="validation-session",
            source_quote="Use SQLite and FTS5 for the first version.",
        ).item

        hits = retrieval.search(project, "SQLite storage")
        if not hits or hits[0].id != original.id:
            raise RuntimeError("search did not retrieve the original SQLite decision")

        replacement = repository.record(
            project=project,
            item_type=ItemType.DECISION,
            title="Use SQLite in WAL mode",
            summary="SQLite remains local while WAL improves read concurrency.",
            body="Use SQLite with FTS5 and enable WAL after opening the database.",
            author=Author.USER,
            source_session="validation-session",
            source_quote="Keep SQLite and enable WAL for concurrent readers.",
            supersedes=original.id,
        )
        stored_original = store.get_item(original.id)
        if stored_original is None or stored_original.status is not ItemStatus.SUPERSEDED:
            raise RuntimeError("supersession did not retire the original decision")
        if replacement.superseded_item is None:
            raise RuntimeError("supersession result did not include the retired item")

        repository.record(
            project=project,
            item_type=ItemType.TASK,
            title="Connect a real MCP client",
            summary="Configure one client and run record, search, get, and resume.",
            body="Use the client configuration from README.md and inspect the persisted database.",
            author=Author.USER,
            source_session="validation-session",
            source_quote="Next, connect this to an MCP client.",
        )
        store.add_session(
            MemorySession(
                goal="Validate the project-memory flow",
                handoff="Core flow passed; the remaining gate is a real MCP client connection.",
            )
        )

        brief = BriefRenderer(store).render(project)
        required_phrases = (
            "Keep the first release local",
            "Use SQLite in WAL mode",
            "Do not use Neo4j",
            "Connect a real MCP client",
            "remaining gate is a real MCP client connection",
        )
        missing = [phrase for phrase in required_phrases if phrase not in brief]
        if missing:
            raise RuntimeError(f"resume brief is missing expected content: {missing}")
        if len(brief) > 6_000:
            raise RuntimeError("resume brief exceeded the conservative 2,000-token character cap")
        return brief


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the core project-memory flow")
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional SQLite path. Omit to use and remove a temporary database.",
    )
    arguments = parser.parse_args()

    temporary: AbstractContextManager[str | None]
    if arguments.database is None:
        temporary = TemporaryDirectory(prefix="mcp-project-memory-")
    else:
        arguments.database.parent.mkdir(parents=True, exist_ok=True)
        temporary = nullcontext(None)

    with temporary as directory:
        database = arguments.database or Path(directory) / "validation.sqlite3"
        brief = validate(database)
        print("Core integration flow passed.")
        if arguments.database is None:
            print("Database: temporary file (removed after validation)")
        else:
            print(f"Database: {database}")
        print()
        print(brief)


if __name__ == "__main__":
    main()
