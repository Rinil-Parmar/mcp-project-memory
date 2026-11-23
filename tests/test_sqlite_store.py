import sqlite3
from pathlib import Path

import pytest

from src.adapters.storage.sqlite_store import DuplicateMemoryError, SQLiteStore
from src.core.schema import Author, ItemStatus, ItemType, LinkRelation, MemoryItem, MemoryLink


def make_item(**overrides: object) -> MemoryItem:
    values = {
        "project": "memory-project",
        "type": ItemType.DECISION,
        "title": "Use SQLite for local storage",
        "summary": "SQLite keeps local installation simple.",
        "body": "The initial adapter uses SQLite and its FTS5 extension.",
        "status": ItemStatus.ACTIVE,
        "author": Author.USER,
        "source_session": "session-001",
        "source_quote": "Use SQLite for the first release.",
    }
    values.update(overrides)
    return MemoryItem(**values)


def test_item_persists_across_store_restarts(tmp_path: Path) -> None:
    database = tmp_path / "memory.sqlite3"
    item = make_item()
    with SQLiteStore(database) as store:
        store.add_item(item)

    with SQLiteStore(database) as store:
        assert store.get_item(item.id) == item


def test_duplicate_semantic_content_is_rejected() -> None:
    first = make_item()
    second = make_item()
    with SQLiteStore() as store:
        store.add_item(first)

        with pytest.raises(DuplicateMemoryError):
            store.add_item(second)


def test_search_finds_title_and_body_terms() -> None:
    item = make_item()
    with SQLiteStore() as store:
        store.add_item(item)

        title_hits = store.search_items(item.project, "SQLite storage")
        body_hits = store.search_items(item.project, "FTS5 extension")

    assert [hit.id for hit in title_hits] == [item.id]
    assert [hit.id for hit in body_hits] == [item.id]


def test_search_is_isolated_by_project_and_status() -> None:
    active = make_item()
    other_project = make_item(project="another-project")
    done = make_item(
        title="Complete SQLite experiment",
        summary="The SQLite experiment is complete.",
        body="SQLite testing is finished.",
        status=ItemStatus.DONE,
    )
    with SQLiteStore() as store:
        store.add_item(active)
        store.add_item(other_project)
        store.add_item(done)

        default_hits = store.search_items(active.project, "SQLite")
        done_hits = store.search_items(active.project, "SQLite", statuses=[ItemStatus.DONE])

    assert [hit.id for hit in default_hits] == [active.id]
    assert [hit.id for hit in done_hits] == [done.id]


def test_link_requires_existing_items() -> None:
    old = make_item()
    new = make_item(title="Use SQLite with WAL", body="Enable WAL mode for local concurrency.")
    link = MemoryLink(src=new.id, dst=old.id, relation=LinkRelation.SUPERSEDES)
    with SQLiteStore() as store:
        store.add_item(old)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            store.add_link(link)

        store.add_item(new)
        store.add_link(link)


def test_search_limit_is_bounded() -> None:
    with SQLiteStore() as store, pytest.raises(ValueError, match="limit"):
        store.search_items("memory-project", "SQLite", limit=51)
