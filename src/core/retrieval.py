"""Compact retrieval service used by transport adapters."""

from __future__ import annotations

from collections.abc import Sequence

from .ports import MemoryStore, SearchHit
from .schema import ItemStatus, MemoryItem


class MemoryRetrieval:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def search(
        self,
        project: str,
        query: str,
        *,
        statuses: Sequence[ItemStatus] | None = None,
        limit: int = 8,
    ) -> list[SearchHit]:
        return self._store.search_items(project, query, statuses=statuses, limit=limit)

    def get(self, ids: Sequence[str]) -> list[MemoryItem]:
        if len(ids) > 20:
            raise ValueError("at most 20 memory items can be fetched at once")
        return [item for item_id in ids if (item := self._store.get_item(item_id)) is not None]
