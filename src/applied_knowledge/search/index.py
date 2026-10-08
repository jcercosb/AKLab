from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from applied_knowledge.storage.models import KnowledgeItemRow


class SearchUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SearchHit:
    knowledge_item_id: str
    origin_key: str
    kind: str
    title: str
    status: str
    score: float | None
    match_type: str


class KnowledgeSearchIndex(Protocol):
    def upsert(self, row: KnowledgeItemRow) -> None: ...


class SqliteFtsIndex:
    table_name = "knowledge_fts"

    def __init__(self, session: Session) -> None:
        if session.bind is None or session.bind.dialect.name != "sqlite":
            raise SearchUnavailableError("F2 FTS baseline currently requires SQLite")
        self.session = session
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.session.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    knowledge_item_id UNINDEXED,
                    knowledge_space_id UNINDEXED,
                    kind UNINDEXED,
                    status UNINDEXED,
                    title,
                    summary,
                    content,
                    sections,
                    attributes,
                    tokenize='unicode61 remove_diacritics 2'
                )
                """
            )
        )

    def rebuild(self, *, knowledge_space_id: str | None = None) -> int:
        stmt = (
            select(KnowledgeItemRow)
            .options(
                selectinload(KnowledgeItemRow.sections),
                selectinload(KnowledgeItemRow.attributes),
            )
            .order_by(KnowledgeItemRow.id)
        )
        if knowledge_space_id is not None:
            stmt = stmt.where(KnowledgeItemRow.knowledge_space_id == knowledge_space_id)
            self.session.execute(
                text("DELETE FROM knowledge_fts WHERE knowledge_space_id = :space"),
                {"space": knowledge_space_id},
            )
        else:
            self.session.execute(text("DELETE FROM knowledge_fts"))

        rows = list(self.session.scalars(stmt))
        for row in rows:
            self._insert(row)
        self.session.flush()
        return len(rows)

    def upsert(self, row: KnowledgeItemRow) -> None:
        self.session.execute(
            text("DELETE FROM knowledge_fts WHERE knowledge_item_id = :item_id"),
            {"item_id": row.id},
        )
        self._insert(row)
        self.session.flush()

    def _insert(self, row: KnowledgeItemRow) -> None:
        sections = "\n".join(
            part
            for section in sorted(row.sections, key=lambda value: value.position)
            for part in (section.title or "", section.content)
            if part
        )
        attributes = "\n".join(
            f"{attribute.name} {attribute.value}"
            for attribute in sorted(row.attributes, key=lambda value: (value.name, value.value))
        )
        self.session.execute(
            text(
                """
                INSERT INTO knowledge_fts (
                    knowledge_item_id,
                    knowledge_space_id,
                    kind,
                    status,
                    title,
                    summary,
                    content,
                    sections,
                    attributes
                ) VALUES (
                    :knowledge_item_id,
                    :knowledge_space_id,
                    :kind,
                    :status,
                    :title,
                    :summary,
                    :content,
                    :sections,
                    :attributes
                )
                """
            ),
            {
                "knowledge_item_id": row.id,
                "knowledge_space_id": row.knowledge_space_id,
                "kind": row.kind,
                "status": row.status,
                "title": row.title or "",
                "summary": row.summary or "",
                "content": row.content or "",
                "sections": sections,
                "attributes": attributes,
            },
        )


def normalize_fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        raise ValueError("Search query must contain at least one searchable token")
    escaped = [token.replace('"', '""') for token in tokens]
    return " OR ".join(f'"{token}"' for token in escaped)
