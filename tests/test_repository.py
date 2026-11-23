import pytest

from src.adapters.storage import DuplicateMemoryError, SQLiteStore
from src.core.repository import MemoryRepository
from src.core.schema import Author, ItemStatus, ItemType


def record_decision(repository: MemoryRepository, **overrides: object):
    values = {
        "project": "memory-project",
        "item_type": ItemType.DECISION,
        "title": "Use SQLite",
        "summary": "SQLite provides local persistence.",
        "body": "Use SQLite with FTS5 for version 0.1.",
        "author": Author.USER,
        "source_session": "session-001",
        "source_quote": "Use SQLite for the MVP.",
    }
    values.update(overrides)
    return repository.record(**values)


def test_user_record_is_active_and_model_record_is_proposed() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)

        user = record_decision(repository)
        model = record_decision(
            repository,
            title="Enable WAL",
            summary="WAL may improve concurrency.",
            body="Consider enabling WAL after measuring contention.",
            author=Author.MODEL,
        )

    assert user.item.status is ItemStatus.ACTIVE
    assert model.item.status is ItemStatus.PROPOSED


def test_duplicate_record_returns_existing_item() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)
        first = record_decision(repository)
        duplicate = record_decision(repository)

        assert duplicate.item.id == first.item.id
        assert len(store.list_items("memory-project")) == 1


def test_supersession_retires_old_item_and_links_new_item_atomically() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)
        old = record_decision(repository).item

        result = record_decision(
            repository,
            title="Use SQLite in WAL mode",
            summary="WAL improves local read concurrency.",
            body="Use SQLite with FTS5 and WAL mode.",
            source_quote="Enable WAL for concurrent readers.",
            supersedes=old.id,
        )

        stored_old = store.get_item(old.id)
        link = store._connection.execute(
            "SELECT src, dst, relation FROM links WHERE src = ?", (result.item.id,)
        ).fetchone()

    assert stored_old is not None
    assert stored_old.status is ItemStatus.SUPERSEDED
    assert stored_old.valid_to is not None
    assert result.superseded_item == stored_old
    assert tuple(link) == (result.item.id, old.id, "supersedes")


def test_model_cannot_supersede_without_confirmation() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)
        old = record_decision(repository).item

        with pytest.raises(ValueError, match="confirmed"):
            record_decision(
                repository,
                title="Use PostgreSQL",
                summary="PostgreSQL could support hosted use.",
                body="Replace local SQLite with PostgreSQL.",
                author=Author.MODEL,
                supersedes=old.id,
            )


def test_failed_supersession_rolls_back_old_status() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)
        old = record_decision(repository).item
        existing = record_decision(
            repository,
            title="Use SQLite with WAL",
            summary="WAL improves concurrency.",
            body="Enable WAL.",
        ).item

        with pytest.raises(DuplicateMemoryError):
            store.supersede_item(old.id, existing)

        assert store.get_item(old.id).status is ItemStatus.ACTIVE


def test_status_transition_confirms_proposal() -> None:
    with SQLiteStore() as store:
        repository = MemoryRepository(store)
        proposed = record_decision(repository, author=Author.MODEL).item

        active = repository.update_status(proposed.id, ItemStatus.ACTIVE)

        assert active.status is ItemStatus.ACTIVE
        assert store.get_item(proposed.id).status is ItemStatus.ACTIVE
