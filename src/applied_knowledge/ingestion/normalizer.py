from __future__ import annotations

from typing import Protocol

from applied_knowledge.domain.models import NormalizedKnowledge, SourceRecord


class KnowledgeNormalizer(Protocol):
    def normalize(self, record: SourceRecord) -> NormalizedKnowledge: ...
