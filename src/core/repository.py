"""Write policy for project memory."""

from __future__ import annotations

from dataclasses import dataclass

from .ports import MemoryStore
from .schema import Author, ItemStatus, ItemType, MemoryItem


@dataclass(frozen=True, slots=True)
class RecordResult:
    item: MemoryItem
    superseded_item: MemoryItem | None = None


class MemoryRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def record(
        self,
        *,
        project: str,
        item_type: ItemType,
        title: str,
        summary: str,
        body: str,
        author: Author,
        source_session: str,
        source_quote: str,
        scope: str = "**",
        priority: int = 50,
        supersedes: str | None = None,
    ) -> RecordResult:
        status = ItemStatus.ACTIVE if author is Author.USER else ItemStatus.PROPOSED
        if supersedes is not None and status is not ItemStatus.ACTIVE:
            raise ValueError("model-authored replacements must be confirmed before supersession")
        item = MemoryItem(
            project=project,
            type=item_type,
            title=title,
            summary=summary,
            body=body,
            status=status,
            priority=priority,
            scope=scope,
            author=author,
            source_session=source_session,
            source_quote=source_quote,
        )
        duplicate = self._store.find_by_content_hash(project, item.content_hash)
        if duplicate is not None:
            return RecordResult(item=duplicate)
        if supersedes is None:
            self._store.add_item(item)
            return RecordResult(item=item)
        retired = self._store.supersede_item(supersedes, item)
        return RecordResult(item=item, superseded_item=retired)

    def update_status(self, item_id: str, status: ItemStatus) -> MemoryItem:
        return self._store.update_status(item_id, status)
