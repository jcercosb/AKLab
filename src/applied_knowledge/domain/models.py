from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One immutable-ish record delivered by a SourceAdapter.

    external_id is stable inside the source. raw_content must preserve the
    original source information needed to reproduce or audit normalization.
    """

    external_id: str
    source_type: str
    raw_content: JsonObject
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeSectionData:
    kind: str
    content: str
    title: str | None = None
    position: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeAttributeData:
    name: str
    value: str
    value_type: str = "string"


@dataclass(frozen=True, slots=True)
class KnowledgeItemData:
    kind: str
    title: str
    content: str | None = None
    summary: str | None = None
    status: str = "active"
    confidence: float | None = None
    sections: tuple[KnowledgeSectionData, ...] = ()
    attributes: tuple[KnowledgeAttributeData, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceData:
    evidence_type: str = "source_record"
    locator: str | None = None
    excerpt: str | None = None
    confidence: float | None = 1.0


@dataclass(frozen=True, slots=True)
class NormalizedKnowledge:
    """Deterministic normalization output for one SourceRecord.

    F0 intentionally allows zero or more knowledge items from one source
    record, even though the first SAT normalizer will normally emit one.
    """

    items: tuple[KnowledgeItemData, ...]
    evidence: EvidenceData = EvidenceData()
