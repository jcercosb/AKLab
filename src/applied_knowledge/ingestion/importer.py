from __future__ import annotations

from dataclasses import dataclass

from .adapter import SourceAdapter
from .normalizer import KnowledgeNormalizer
from applied_knowledge.storage.repository import KnowledgeRepository


@dataclass(frozen=True, slots=True)
class ImportResult:
    new: int = 0
    changed: int = 0
    unchanged: int = 0
    knowledge_items: int = 0


class Importer:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def run(
        self,
        *,
        knowledge_space_id: str,
        source_id: str,
        adapter: SourceAdapter,
        normalizer: KnowledgeNormalizer,
    ) -> ImportResult:
        run = self.repository.begin_import(
            source_id=source_id,
            adapter=adapter.name,
            adapter_version=adapter.version,
            source_fingerprint=adapter.fingerprint(),
        )
        counters = {"new": 0, "changed": 0, "unchanged": 0, "knowledge_items": 0}
        try:
            for record in adapter.records():
                upsert = self.repository.upsert_source_item(source_id=source_id, record=record, run_id=run.id)
                counters[upsert.state] += 1

                # Unchanged records already have deterministic normalized data.
                if upsert.state == "unchanged":
                    continue

                normalized = normalizer.normalize(record)
                for index, item in enumerate(normalized.items):
                    self.repository.upsert_normalized_item(
                        knowledge_space_id=knowledge_space_id,
                        source_id=source_id,
                        source_item=upsert.row,
                        item_index=index,
                        item=item,
                        evidence_type=normalized.evidence.evidence_type,
                        evidence_locator=normalized.evidence.locator,
                        evidence_excerpt=normalized.evidence.excerpt,
                        evidence_confidence=normalized.evidence.confidence,
                    )
                    counters["knowledge_items"] += 1
        except Exception:
            self.repository.finish_import(run, status="failed", stats=counters)
            raise
        self.repository.finish_import(run, status="completed", stats=counters)
        return ImportResult(**counters)
