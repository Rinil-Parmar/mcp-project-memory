"""SQLite + FTS5 implementation of the memory storage port."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Self

from src.core.ports import SearchHit
from src.core.schema import (
    ItemStatus,
    LinkRelation,
    MemoryItem,
    MemoryLink,
    MemorySession,
    utc_now,
)


class DuplicateMemoryError(ValueError):
    """Raised when an item with the same project and content already exists."""


class SQLiteStore:
    def __init__(self, database: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(database))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _migrate(self) -> None:
        try:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    scope TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    recorded_at TEXT NOT NULL,
                    retired_at TEXT,
                    author TEXT NOT NULL,
                    source_session TEXT NOT NULL,
                    source_quote TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    UNIQUE(project, content_hash)
                );

                CREATE INDEX IF NOT EXISTS idx_items_project_status
                    ON items(project, status);
                CREATE INDEX IF NOT EXISTS idx_items_project_scope
                    ON items(project, scope);

                CREATE TABLE IF NOT EXISTS links (
                    src TEXT NOT NULL REFERENCES items(id),
                    dst TEXT NOT NULL REFERENCES items(id),
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(src, dst, relation)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    handoff TEXT
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                    item_id UNINDEXED,
                    project UNINDEXED,
                    title,
                    summary,
                    body,
                    scope,
                    tokenize='unicode61 tokenchars ''_-/'''
                );
                """
            )
        except sqlite3.OperationalError as exc:
            if "fts5" in str(exc).lower():
                raise RuntimeError("This Python SQLite build does not include FTS5") from exc
            raise

    def add_item(self, item: MemoryItem) -> None:
        try:
            with self._connection:
                self._insert_item(item)
        except sqlite3.IntegrityError as exc:
            self._raise_domain_integrity_error(item, exc)

    def _insert_item(self, item: MemoryItem) -> None:
        values = item.to_dict()
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        self._connection.execute(
            f"INSERT INTO items ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values[column] for column in columns),
        )
        self._connection.execute(
            """
            INSERT INTO items_fts(item_id, project, title, summary, body, scope)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item.id, item.project, item.title, item.summary, item.body, item.scope),
        )

    @staticmethod
    def _raise_domain_integrity_error(item: MemoryItem, exc: sqlite3.IntegrityError) -> None:
        if "content_hash" in str(exc) or "items.project" in str(exc):
            raise DuplicateMemoryError(
                f"an identical memory already exists in project {item.project!r}"
            ) from exc
        raise exc

    def get_item(self, item_id: str) -> MemoryItem | None:
        row = self._connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return MemoryItem.from_dict(dict(row)) if row is not None else None

    def find_by_content_hash(self, project: str, content_hash: str) -> MemoryItem | None:
        row = self._connection.execute(
            "SELECT * FROM items WHERE project = ? AND content_hash = ?",
            (project, content_hash),
        ).fetchone()
        return MemoryItem.from_dict(dict(row)) if row is not None else None

    def search_items(
        self,
        project: str,
        query: str,
        *,
        statuses: Sequence[ItemStatus] | None = None,
        limit: int = 8,
    ) -> list[SearchHit]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        match_query = self._to_fts_query(query)
        if not match_query:
            return []

        selected_statuses = tuple(statuses or (ItemStatus.ACTIVE, ItemStatus.PROPOSED))
        if not selected_statuses:
            return []
        placeholders = ", ".join("?" for _ in selected_statuses)
        rows = self._connection.execute(
            f"""
            SELECT i.id, i.type, i.status, i.title, i.summary, i.scope, i.recorded_at,
                   bm25(items_fts, 0.0, 0.0, 5.0, 2.0, 1.0, 1.0) AS rank
            FROM items_fts
            JOIN items AS i ON i.id = items_fts.item_id
            WHERE items_fts MATCH ?
              AND i.project = ?
              AND i.status IN ({placeholders})
            ORDER BY rank, i.recorded_at DESC
            LIMIT ?
            """,
            (match_query, project, *(status.value for status in selected_statuses), limit),
        ).fetchall()
        return [SearchHit(**dict(row)) for row in rows]

    @staticmethod
    def _to_fts_query(query: str) -> str:
        tokens = re.findall(r"[\w./:-]+", query, flags=re.UNICODE)
        return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)

    def add_link(self, link: MemoryLink) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO links(src, dst, relation, created_at) VALUES (?, ?, ?, ?)",
                (link.src, link.dst, link.relation.value, link.created_at.isoformat()),
            )

    def add_session(self, session: MemorySession) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO sessions(id, goal, started_at, ended_at, handoff)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.goal,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.handoff,
                ),
            )

    def supersede_item(self, old_item_id: str, new_item: MemoryItem) -> MemoryItem:
        old_item = self.get_item(old_item_id)
        if old_item is None:
            raise KeyError(f"memory item {old_item_id!r} does not exist")
        if old_item.project != new_item.project:
            raise ValueError("supersession cannot cross project boundaries")
        if old_item.type != new_item.type:
            raise ValueError("a memory item can only supersede another item of the same type")
        if old_item.status not in (ItemStatus.ACTIVE, ItemStatus.PROPOSED):
            raise ValueError(f"cannot supersede an item with status {old_item.status.value!r}")
        if new_item.status is not ItemStatus.ACTIVE:
            raise ValueError("the replacement item must be active")

        retired_at = max(new_item.recorded_at, old_item.recorded_at)
        valid_to = max(new_item.valid_from, old_item.valid_from)
        retired = replace(
            old_item,
            status=ItemStatus.SUPERSEDED,
            valid_to=valid_to,
            retired_at=retired_at,
        )
        try:
            with self._connection:
                self._connection.execute(
                    """
                    UPDATE items SET status = ?, valid_to = ?, retired_at = ? WHERE id = ?
                    """,
                    (
                        retired.status.value,
                        retired.valid_to.isoformat(),
                        retired.retired_at.isoformat(),
                        retired.id,
                    ),
                )
                self._insert_item(new_item)
                self._connection.execute(
                    "INSERT INTO links(src, dst, relation, created_at) VALUES (?, ?, ?, ?)",
                    (
                        new_item.id,
                        old_item.id,
                        LinkRelation.SUPERSEDES.value,
                        retired_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            self._raise_domain_integrity_error(new_item, exc)
        return retired

    def update_status(self, item_id: str, status: ItemStatus) -> MemoryItem:
        item = self.get_item(item_id)
        if item is None:
            raise KeyError(f"memory item {item_id!r} does not exist")
        allowed = {
            ItemStatus.PROPOSED: {ItemStatus.ACTIVE, ItemStatus.REJECTED},
            ItemStatus.ACTIVE: {ItemStatus.DONE, ItemStatus.REJECTED},
            ItemStatus.DONE: set(),
            ItemStatus.REJECTED: set(),
            ItemStatus.SUPERSEDED: set(),
        }
        if status == item.status:
            return item
        if status not in allowed[item.status]:
            raise ValueError(f"invalid status transition: {item.status.value} -> {status.value}")
        retired_at = utc_now() if status in (ItemStatus.DONE, ItemStatus.REJECTED) else None
        updated = replace(item, status=status, retired_at=retired_at)
        with self._connection:
            self._connection.execute(
                "UPDATE items SET status = ?, retired_at = ? WHERE id = ?",
                (
                    updated.status.value,
                    updated.retired_at.isoformat() if updated.retired_at else None,
                    updated.id,
                ),
            )
        return updated

    def list_items(
        self,
        project: str,
        *,
        statuses: Sequence[ItemStatus] | None = None,
        limit: int = 100,
    ) -> list[MemoryItem]:
        if not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        parameters: list[str | int] = [project]
        status_clause = ""
        if statuses is not None:
            if not statuses:
                return []
            placeholders = ", ".join("?" for _ in statuses)
            status_clause = f" AND status IN ({placeholders})"
            parameters.extend(status.value for status in statuses)
        parameters.append(limit)
        rows = self._connection.execute(
            f"""
            SELECT * FROM items
            WHERE project = ? {status_clause}
            ORDER BY priority ASC, recorded_at DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        return [MemoryItem.from_dict(dict(row)) for row in rows]

    def latest_session(self) -> MemorySession | None:
        row = self._connection.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        values = dict(row)
        for name in ("started_at", "ended_at"):
            if values[name] is not None:
                values[name] = datetime.fromisoformat(values[name])
        return MemorySession(**values)
