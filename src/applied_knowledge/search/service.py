from __future__ import annotations

from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.orm import Session

from applied_knowledge.storage.models import KnowledgeAttributeRow, KnowledgeItemRow
from applied_knowledge.storage.repository import KnowledgeRepository

from .index import SearchHit, SqliteFtsIndex, normalize_fts_query


class SearchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = KnowledgeRepository(session)

    def exact(
        self,
        *,
        knowledge_space_id: str,
        query: str | None = None,
        kind: str | None = None,
        status: str | None = "active",
        attribute_name: str | None = None,
        attribute_value: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self._require_space(knowledge_space_id)
        stmt = select(KnowledgeItemRow).where(
            KnowledgeItemRow.knowledge_space_id == knowledge_space_id
        )
        if query is not None:
            folded = query.casefold()
            attribute_match = exists(
                select(KnowledgeAttributeRow.id).where(
                    KnowledgeAttributeRow.knowledge_item_id == KnowledgeItemRow.id,
                    func.lower(KnowledgeAttributeRow.value) == folded,
                )
            )
            stmt = stmt.where(
                or_(
                    func.lower(KnowledgeItemRow.title) == folded,
                    func.lower(KnowledgeItemRow.origin_key) == folded,
                    attribute_match,
                )
            )
        if kind is not None:
            stmt = stmt.where(KnowledgeItemRow.kind == kind)
        if status is not None:
            stmt = stmt.where(KnowledgeItemRow.status == status)
        stmt = self._apply_attribute_filter(
            stmt,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
        )
        stmt = stmt.order_by(KnowledgeItemRow.title, KnowledgeItemRow.id).limit(limit)
        return [self._row_hit(row, match_type="exact") for row in self.session.scalars(stmt)]

    def fts(
        self,
        *,
        knowledge_space_id: str,
        query: str,
        kind: str | None = None,
        status: str | None = "active",
        attribute_name: str | None = None,
        attribute_value: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self._require_space(knowledge_space_id)
        SqliteFtsIndex(self.session).ensure_schema()
        normalized = normalize_fts_query(query)

        conditions = [
            "fts.knowledge_space_id = :knowledge_space_id",
            "knowledge_fts MATCH :query",
        ]
        params: dict[str, object] = {
            "knowledge_space_id": knowledge_space_id,
            "query": normalized,
            "limit": limit,
        }
        if kind is not None:
            conditions.append("ki.kind = :kind")
            params["kind"] = kind
        if status is not None:
            conditions.append("ki.status = :status")
            params["status"] = status
        if attribute_name is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM knowledge_attributes ka "
                "WHERE ka.knowledge_item_id = ki.id AND ka.name = :attribute_name"
                + (" AND ka.value = :attribute_value" if attribute_value is not None else "")
                + ")"
            )
            params["attribute_name"] = attribute_name
            if attribute_value is not None:
                params["attribute_value"] = attribute_value
        elif attribute_value is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM knowledge_attributes ka "
                "WHERE ka.knowledge_item_id = ki.id AND ka.value = :attribute_value)"
            )
            params["attribute_value"] = attribute_value

        sql = text(
            f"""
            SELECT
                ki.id AS knowledge_item_id,
                ki.origin_key AS origin_key,
                ki.kind AS kind,
                ki.title AS title,
                ki.status AS status,
                -bm25(knowledge_fts, 0.0, 0.0, 0.0, 0.0, 5.0, 3.0, 2.0, 2.0, 4.0) AS score
            FROM knowledge_fts AS fts
            JOIN knowledge_items AS ki ON ki.id = fts.knowledge_item_id
            WHERE {' AND '.join(conditions)}
            ORDER BY bm25(knowledge_fts, 0.0, 0.0, 0.0, 0.0, 5.0, 3.0, 2.0, 2.0, 4.0), ki.id
            LIMIT :limit
            """
        )
        rows = self.session.execute(sql, params).mappings().all()
        return [
            SearchHit(
                knowledge_item_id=row["knowledge_item_id"],
                origin_key=row["origin_key"],
                kind=row["kind"],
                title=row["title"],
                status=row["status"],
                score=float(row["score"]),
                match_type="fts",
            )
            for row in rows
        ]

    def _apply_attribute_filter(
        self,
        stmt,
        *,
        attribute_name: str | None,
        attribute_value: str | None,
    ):
        if attribute_name is None and attribute_value is None:
            return stmt
        criteria = [KnowledgeAttributeRow.knowledge_item_id == KnowledgeItemRow.id]
        if attribute_name is not None:
            criteria.append(KnowledgeAttributeRow.name == attribute_name)
        if attribute_value is not None:
            criteria.append(KnowledgeAttributeRow.value == attribute_value)
        return stmt.where(exists(select(KnowledgeAttributeRow.id).where(*criteria)))

    def _require_space(self, knowledge_space_id: str) -> None:
        if self.repository.get_space(knowledge_space_id) is None:
            raise LookupError(f"KnowledgeSpace not found: {knowledge_space_id}")

    @staticmethod
    def _row_hit(row: KnowledgeItemRow, *, match_type: str) -> SearchHit:
        return SearchHit(
            knowledge_item_id=row.id,
            origin_key=row.origin_key,
            kind=row.kind,
            title=row.title,
            status=row.status,
            score=None,
            match_type=match_type,
        )
