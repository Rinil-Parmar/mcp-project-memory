from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from src.core.schema import (
    Author,
    DomainValidationError,
    ItemStatus,
    ItemType,
    LinkRelation,
    MemoryItem,
    MemoryLink,
    MemorySession,
)


def make_item(**overrides: object) -> MemoryItem:
    values = {
        "project": "memory-project",
        "type": ItemType.DECISION,
        "title": "Use SQLite for local storage",
        "summary": "SQLite keeps the local setup self-contained.",
        "body": "Use SQLite with FTS5 for the first release.",
        "status": ItemStatus.ACTIVE,
        "author": Author.USER,
        "source_session": "session-001",
        "source_quote": "Let's use SQLite for the first release.",
    }
    values.update(overrides)
    return MemoryItem(**values)


def test_item_round_trips_through_dictionary() -> None:
    item = make_item()

    restored = MemoryItem.from_dict(item.to_dict())

    assert restored == item


def test_content_hash_is_stable_and_excludes_record_identity() -> None:
    first = make_item()
    second = make_item()

    assert first.id != second.id
    assert first.content_hash == second.content_hash


def test_content_hash_changes_with_semantic_content() -> None:
    item = make_item()

    changed = replace(item, body="Use PostgreSQL instead.", content_hash="")

    assert changed.content_hash != item.content_hash


@pytest.mark.parametrize("field", ["project", "title", "summary", "body", "source_quote"])
def test_required_text_rejects_blank_values(field: str) -> None:
    with pytest.raises(DomainValidationError, match=field):
        make_item(**{field: "   "})


def test_priority_must_stay_in_range() -> None:
    with pytest.raises(DomainValidationError, match="priority"):
        make_item(priority=101)


def test_datetimes_must_be_timezone_aware() -> None:
    with pytest.raises(DomainValidationError, match="timezone"):
        make_item(valid_from=datetime.now())


def test_validity_range_must_be_ordered() -> None:
    now = datetime.now(UTC)
    with pytest.raises(DomainValidationError, match="valid_to"):
        make_item(valid_from=now, valid_to=now - timedelta(seconds=1))


def test_link_cannot_reference_itself() -> None:
    item = make_item()
    with pytest.raises(DomainValidationError, match="itself"):
        MemoryLink(src=item.id, dst=item.id, relation=LinkRelation.RELATES_TO)


def test_session_end_cannot_precede_start() -> None:
    now = datetime.now(UTC)
    with pytest.raises(DomainValidationError, match="ended_at"):
        MemorySession(goal="Build the schema", started_at=now, ended_at=now - timedelta(seconds=1))
