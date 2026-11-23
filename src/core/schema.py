"""Domain models for project memory.

This module intentionally depends only on the Python standard library. Transport and storage
adapters translate these models at the boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class DomainValidationError(ValueError):
    """Raised when a memory record violates a domain invariant."""


class ItemType(StrEnum):
    DECISION = "decision"
    CONSTRAINT = "constraint"
    REJECTED = "rejected"
    INTERFACE = "interface"
    SCHEMA = "schema"
    TASK = "task"
    EPISODE = "episode"


class ItemStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DONE = "done"
    REJECTED = "rejected"


class Author(StrEnum):
    USER = "user"
    MODEL = "model"


class LinkRelation(StrEnum):
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    CONTRADICTS = "contradicts"
    RELATES_TO = "relates_to"


def utc_now() -> datetime:
    return datetime.now(UTC)


def _require_text(name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise DomainValidationError(f"{name} must not be empty")
    return cleaned


def _require_aware(name: str, value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise DomainValidationError(f"{name} must include timezone information")
    return value


def _require_uuid(name: str, value: str) -> str:
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise DomainValidationError(f"{name} must be a valid UUID") from exc
    return value


def compute_content_hash(
    *,
    project: str,
    item_type: ItemType,
    title: str,
    summary: str,
    body: str,
    scope: str,
) -> str:
    """Return a stable hash for semantic content used by duplicate detection."""

    payload = {
        "body": body.strip(),
        "project": project.strip(),
        "scope": scope.strip(),
        "summary": summary.strip(),
        "title": title.strip(),
        "type": item_type.value,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MemoryItem:
    project: str
    type: ItemType
    title: str
    summary: str
    body: str
    author: Author
    source_session: str
    source_quote: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: ItemStatus = ItemStatus.PROPOSED
    priority: int = 50
    scope: str = "**"
    valid_from: datetime = field(default_factory=utc_now)
    valid_to: datetime | None = None
    recorded_at: datetime = field(default_factory=utc_now)
    retired_at: datetime | None = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_uuid("id", self.id))
        for name in ("project", "title", "summary", "body", "source_session", "source_quote"):
            object.__setattr__(self, name, _require_text(name, getattr(self, name)))
        object.__setattr__(self, "scope", _require_text("scope", self.scope))

        if not 0 <= self.priority <= 100:
            raise DomainValidationError("priority must be between 0 and 100")
        for name in ("valid_from", "valid_to", "recorded_at", "retired_at"):
            _require_aware(name, getattr(self, name))
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise DomainValidationError("valid_to cannot be earlier than valid_from")
        if self.retired_at is not None and self.retired_at < self.recorded_at:
            raise DomainValidationError("retired_at cannot be earlier than recorded_at")

        expected_hash = compute_content_hash(
            project=self.project,
            item_type=self.type,
            title=self.title,
            summary=self.summary,
            body=self.body,
            scope=self.scope,
        )
        if self.content_hash and self.content_hash != expected_hash:
            raise DomainValidationError("content_hash does not match the record content")
        object.__setattr__(self, "content_hash", expected_hash)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, StrEnum):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        values = dict(data)
        values["type"] = ItemType(values["type"])
        values["status"] = ItemStatus(values["status"])
        values["author"] = Author(values["author"])
        for name in ("valid_from", "valid_to", "recorded_at", "retired_at"):
            if values.get(name) is not None and not isinstance(values[name], datetime):
                values[name] = datetime.fromisoformat(values[name])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class MemoryLink:
    src: str
    dst: str
    relation: LinkRelation
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_uuid("src", self.src)
        _require_uuid("dst", self.dst)
        _require_aware("created_at", self.created_at)
        if self.src == self.dst:
            raise DomainValidationError("a memory item cannot link to itself")


@dataclass(frozen=True, slots=True)
class MemorySession:
    goal: str
    id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
    handoff: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_uuid("id", self.id))
        object.__setattr__(self, "goal", _require_text("goal", self.goal))
        _require_aware("started_at", self.started_at)
        _require_aware("ended_at", self.ended_at)
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise DomainValidationError("ended_at cannot be earlier than started_at")
        if self.handoff is not None:
            object.__setattr__(self, "handoff", _require_text("handoff", self.handoff))
