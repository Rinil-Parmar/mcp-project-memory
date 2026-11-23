"""Interfaces implemented by storage adapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .schema import ItemStatus, MemoryItem, MemoryLink, MemorySession


@dataclass(frozen=True, slots=True)
class SearchHit:
    id: str
    type: str
    status: str
    title: str
    summary: str
    scope: str
    recorded_at: str
    rank: float


class MemoryStore(Protocol):
    def add_item(self, item: MemoryItem) -> None: ...

    def get_item(self, item_id: str) -> MemoryItem | None: ...

    def find_by_content_hash(self, project: str, content_hash: str) -> MemoryItem | None: ...

    def search_items(
        self,
        project: str,
        query: str,
        *,
        statuses: Sequence[ItemStatus] | None = None,
        limit: int = 8,
    ) -> list[SearchHit]: ...

    def add_link(self, link: MemoryLink) -> None: ...

    def add_session(self, session: MemorySession) -> None: ...

    def supersede_item(self, old_item_id: str, new_item: MemoryItem) -> MemoryItem: ...

    def update_status(self, item_id: str, status: ItemStatus) -> MemoryItem: ...

    def list_items(
        self,
        project: str,
        *,
        statuses: Sequence[ItemStatus] | None = None,
        limit: int = 100,
    ) -> list[MemoryItem]: ...

    def latest_session(self) -> MemorySession | None: ...
