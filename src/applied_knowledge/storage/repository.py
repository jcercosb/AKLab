from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from applied_knowledge.domain.models import KnowledgeItemData, SourceRecord
from .models import (
    EvidenceRow,
    ImportRunRow,
    KnowledgeAttributeRow,
    KnowledgeItemRow,
    KnowledgeSectionRow,
    KnowledgeSpaceRow,
    SourceItemRow,
    SourceRow,
)

_NAMESPACE = uuid.UUID("c5e79ef4-e5d0-4f2b-b6c2-0a5b89af44ee")


def stable_uuid(*parts: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))


def canonical_checksum(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceItemUpsert:
    row: SourceItemRow
    state: str  # new | changed | unchanged


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_space(self, *, id: str, name: str, description: str | None = None) -> KnowledgeSpaceRow:
        row = self.session.get(KnowledgeSpaceRow, id)
        if row is None:
            row = KnowledgeSpaceRow(id=id, name=name, description=description, metadata_json={})
            self.session.add(row)
        else:
            row.name = name
            row.description = description
        self.session.flush()
        return row

    def ensure_source(
        self,
        *,
        id: str,
        knowledge_space_id: str,
        type: str,
        name: str,
        configuration: dict[str, Any] | None = None,
    ) -> SourceRow:
        row = self.session.get(SourceRow, id)
        if row is None:
            row = SourceRow(
                id=id,
                knowledge_space_id=knowledge_space_id,
                type=type,
                name=name,
                configuration=configuration or {},
            )
            self.session.add(row)
        else:
            row.type = type
            row.name = name
            row.configuration = configuration or {}
        self.session.flush()
        return row

    def begin_import(
        self,
        *,
        source_id: str,
        adapter: str,
        adapter_version: str,
        source_fingerprint: str | None = None,
    ) -> ImportRunRow:
        row = ImportRunRow(
            id=str(uuid.uuid4()),
            source_id=source_id,
            adapter=adapter,
            adapter_version=adapter_version,
            source_fingerprint=source_fingerprint,
            status="running",
            stats={},
        )
        self.session.add(row)
        self.session.flush()
        return row

    def finish_import(self, run: ImportRunRow, *, status: str, stats: dict[str, int]) -> None:
        run.status = status
        run.stats = stats
        run.finished_at = datetime.now(timezone.utc)
        self.session.flush()

    def upsert_source_item(self, *, source_id: str, record: SourceRecord, run_id: str) -> SourceItemUpsert:
        checksum = canonical_checksum(record.raw_content)
        row = self.session.scalar(
            select(SourceItemRow).where(
                SourceItemRow.source_id == source_id,
                SourceItemRow.external_id == record.external_id,
            )
        )
        if row is None:
            row = SourceItemRow(
                id=stable_uuid("source-item", source_id, record.external_id),
                source_id=source_id,
                external_id=record.external_id,
                parent_external_id=record.parent_external_id,
                source_type=record.source_type,
                raw_content=record.raw_content,
                metadata_json=record.metadata,
                checksum=checksum,
                last_seen_run_id=run_id,
            )
            self.session.add(row)
            state = "new"
        elif row.checksum == checksum:
            row.parent_external_id = record.parent_external_id
            row.source_type = record.source_type
            row.metadata_json = record.metadata
            row.last_seen_run_id = run_id
            state = "unchanged"
        else:
            row.parent_external_id = record.parent_external_id
            row.source_type = record.source_type
            row.raw_content = record.raw_content
            row.metadata_json = record.metadata
            row.checksum = checksum
            row.imported_at = datetime.now(timezone.utc)
            row.last_seen_run_id = run_id
            state = "changed"
        self.session.flush()
        return SourceItemUpsert(row=row, state=state)

    def upsert_normalized_item(
        self,
        *,
        knowledge_space_id: str,
        source_id: str,
        source_item: SourceItemRow,
        item_index: int,
        item: KnowledgeItemData,
        evidence_type: str,
        evidence_locator: str | None,
        evidence_excerpt: str | None,
        evidence_confidence: float | None,
    ) -> KnowledgeItemRow:
        origin_key = f"{source_id}:{source_item.external_id}:{item_index}"
        row = self.session.scalar(
            select(KnowledgeItemRow).where(
                KnowledgeItemRow.knowledge_space_id == knowledge_space_id,
                KnowledgeItemRow.origin_key == origin_key,
            )
        )
        if row is None:
            row = KnowledgeItemRow(
                id=stable_uuid("knowledge-item", knowledge_space_id, origin_key),
                knowledge_space_id=knowledge_space_id,
                origin_key=origin_key,
                kind=item.kind,
                title=item.title,
                summary=item.summary,
                content=item.content,
                status=item.status,
                confidence=item.confidence,
            )
            self.session.add(row)
            self.session.flush()
        else:
            row.kind = item.kind
            row.title = item.title
            row.summary = item.summary
            row.content = item.content
            row.status = item.status
            row.confidence = item.confidence
            row.updated_at = datetime.now(timezone.utc)
            self.session.flush()

        self.session.execute(delete(KnowledgeSectionRow).where(KnowledgeSectionRow.knowledge_item_id == row.id))
        self.session.execute(delete(KnowledgeAttributeRow).where(KnowledgeAttributeRow.knowledge_item_id == row.id))

        for section in item.sections:
            self.session.add(
                KnowledgeSectionRow(
                    id=str(uuid.uuid4()),
                    knowledge_item_id=row.id,
                    kind=section.kind,
                    title=section.title,
                    content=section.content,
                    position=section.position,
                )
            )
        for attribute in item.attributes:
            self.session.add(
                KnowledgeAttributeRow(
                    id=str(uuid.uuid4()),
                    knowledge_item_id=row.id,
                    name=attribute.name,
                    value=attribute.value,
                    value_type=attribute.value_type,
                )
            )

        evidence = self.session.scalar(
            select(EvidenceRow).where(
                EvidenceRow.knowledge_item_id == row.id,
                EvidenceRow.source_item_id == source_item.id,
                EvidenceRow.evidence_type == evidence_type,
            )
        )
        if evidence is None:
            evidence = EvidenceRow(
                id=str(uuid.uuid4()),
                knowledge_item_id=row.id,
                source_item_id=source_item.id,
                evidence_type=evidence_type,
                locator=evidence_locator,
                excerpt=evidence_excerpt,
                confidence=evidence_confidence,
            )
            self.session.add(evidence)
        else:
            evidence.locator = evidence_locator
            evidence.excerpt = evidence_excerpt
            evidence.confidence = evidence_confidence

        self.session.flush()
        return row
