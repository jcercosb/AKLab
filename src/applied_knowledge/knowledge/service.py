from __future__ import annotations

from dataclasses import replace
import uuid

from applied_knowledge.domain.models import (
    KnowledgeAttributeData,
    KnowledgeItemData,
    KnowledgeSectionData,
    SourceRecord,
)
from applied_knowledge.storage.models import KnowledgeItemRow, SourceItemRow
from applied_knowledge.storage.repository import KnowledgeRepository
from applied_knowledge.search.index import KnowledgeSearchIndex


class KnowledgeNotFoundError(LookupError):
    pass


class KnowledgeNotManualError(ValueError):
    pass


def manual_source_id(knowledge_space_id: str) -> str:
    return f"manual:{knowledge_space_id}"


def _serialize_item(item: KnowledgeItemData) -> dict[str, object]:
    return {
        "kind": item.kind,
        "title": item.title,
        "summary": item.summary,
        "content": item.content,
        "status": item.status,
        "confidence": item.confidence,
        "sections": [
            {
                "kind": section.kind,
                "title": section.title,
                "content": section.content,
                "position": section.position,
            }
            for section in item.sections
        ],
        "attributes": [
            {
                "name": attribute.name,
                "value": attribute.value,
                "value_type": attribute.value_type,
            }
            for attribute in item.attributes
        ],
    }


def _row_to_item(row: KnowledgeItemRow) -> KnowledgeItemData:
    return KnowledgeItemData(
        kind=row.kind,
        title=row.title,
        summary=row.summary,
        content=row.content,
        status=row.status,
        confidence=row.confidence,
        sections=tuple(
            KnowledgeSectionData(
                kind=section.kind,
                title=section.title,
                content=section.content,
                position=section.position,
            )
            for section in sorted(row.sections, key=lambda value: value.position)
        ),
        attributes=tuple(
            KnowledgeAttributeData(
                name=attribute.name,
                value=attribute.value,
                value_type=attribute.value_type,
            )
            for attribute in row.attributes
        ),
    )


class ManualKnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        search_index: KnowledgeSearchIndex | None = None,
    ) -> None:
        self.repository = repository
        self.search_index = search_index

    def create(
        self,
        *,
        knowledge_space_id: str,
        item: KnowledgeItemData,
    ) -> KnowledgeItemRow:
        if self.repository.get_space(knowledge_space_id) is None:
            raise KnowledgeNotFoundError(f"KnowledgeSpace not found: {knowledge_space_id}")

        source_id = manual_source_id(knowledge_space_id)
        self.repository.ensure_source(
            id=source_id,
            knowledge_space_id=knowledge_space_id,
            type="manual",
            name="Manual knowledge",
            configuration={},
        )

        external_id = f"MANUAL:{uuid.uuid4()}"
        record = SourceRecord(
            external_id=external_id,
            source_type="manual_entry",
            raw_content=_serialize_item(item),
            metadata={"entry_mode": "manual"},
        )
        source_item = self.repository.upsert_source_item(
            source_id=source_id,
            record=record,
            run_id=None,
        ).row
        row = self._store_item(
            knowledge_space_id=knowledge_space_id,
            source_id=source_id,
            source_item=source_item,
            item=item,
        )
        self.repository.add_knowledge_revision(
            knowledge_item_id=row.id,
            snapshot=_serialize_item(item),
            author_type="human",
        )
        if self.search_index is not None:
            self.search_index.upsert(row)
        return row

    def get(self, *, knowledge_space_id: str, knowledge_item_id: str) -> KnowledgeItemRow:
        row = self.repository.get_knowledge_item(knowledge_item_id)
        if row is None or row.knowledge_space_id != knowledge_space_id:
            raise KnowledgeNotFoundError(f"KnowledgeItem not found: {knowledge_item_id}")
        return row

    def list(
        self,
        *,
        knowledge_space_id: str,
        kind: str | None = None,
        status: str | None = "active",
    ) -> list[KnowledgeItemRow]:
        if self.repository.get_space(knowledge_space_id) is None:
            raise KnowledgeNotFoundError(f"KnowledgeSpace not found: {knowledge_space_id}")
        return self.repository.list_knowledge_items(
            knowledge_space_id=knowledge_space_id,
            kind=kind,
            status=status,
        )

    def update(
        self,
        *,
        knowledge_space_id: str,
        knowledge_item_id: str,
        changes: dict[str, object],
    ) -> KnowledgeItemRow:
        row = self.get(
            knowledge_space_id=knowledge_space_id,
            knowledge_item_id=knowledge_item_id,
        )
        source_id = manual_source_id(knowledge_space_id)
        source_item = self.repository.get_evidence_source_item(
            knowledge_item_id=knowledge_item_id,
            source_id=source_id,
            evidence_type="manual_entry",
        )
        if source_item is None:
            raise KnowledgeNotManualError(
                f"KnowledgeItem is not manually maintained: {knowledge_item_id}"
            )

        current = _row_to_item(row)
        allowed = {
            "kind",
            "title",
            "summary",
            "content",
            "status",
            "confidence",
            "sections",
            "attributes",
        }
        unexpected = set(changes) - allowed
        if unexpected:
            raise ValueError(f"Unsupported fields: {sorted(unexpected)}")

        if not changes:
            raise ValueError("At least one field must be changed")

        updated = replace(current, **changes)
        record = SourceRecord(
            external_id=source_item.external_id,
            source_type="manual_entry",
            raw_content=_serialize_item(updated),
            metadata={"entry_mode": "manual"},
        )
        updated_source_item = self.repository.upsert_source_item(
            source_id=source_id,
            record=record,
            run_id=None,
        ).row
        row = self._store_item(
            knowledge_space_id=knowledge_space_id,
            source_id=source_id,
            source_item=updated_source_item,
            item=updated,
        )
        self.repository.add_knowledge_revision(
            knowledge_item_id=row.id,
            snapshot=_serialize_item(updated),
            author_type="human",
        )
        if self.search_index is not None:
            self.search_index.upsert(row)
        return row

    def archive(self, *, knowledge_space_id: str, knowledge_item_id: str) -> KnowledgeItemRow:
        return self.update(
            knowledge_space_id=knowledge_space_id,
            knowledge_item_id=knowledge_item_id,
            changes={"status": "archived"},
        )

    def _store_item(
        self,
        *,
        knowledge_space_id: str,
        source_id: str,
        source_item: SourceItemRow,
        item: KnowledgeItemData,
    ) -> KnowledgeItemRow:
        excerpt = item.content or item.summary or item.title
        return self.repository.upsert_normalized_item(
            knowledge_space_id=knowledge_space_id,
            source_id=source_id,
            source_item=source_item,
            item_index=0,
            item=item,
            evidence_type="manual_entry",
            evidence_locator=source_item.external_id,
            evidence_excerpt=excerpt,
            evidence_confidence=1.0,
        )
