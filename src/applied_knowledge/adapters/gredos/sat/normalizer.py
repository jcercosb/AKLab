from __future__ import annotations

from applied_knowledge.domain.models import (
    EvidenceData,
    KnowledgeAttributeData,
    KnowledgeItemData,
    KnowledgeSectionData,
    NormalizedKnowledge,
    SourceRecord,
)


class GredosSatNormalizer:
    """F0 deterministic mapping. No LLM and no inferred domain knowledge."""

    SECTION_MAP = (
        ("SINTOMAS", "symptom"),
        ("ENTORNO", "environment"),
        ("SOLUCION", "solution"),
        ("OBSERVACIONES", "notes"),
    )
    ATTRIBUTE_MAP = (
        ("PROGRAMA", "program"),
        ("MODULO", "module"),
    )

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def normalize(self, record: SourceRecord) -> NormalizedKnowledge:
        table = record.metadata.get("table")
        if table is not None and table != "CONSULTAS":
            return NormalizedKnowledge(items=())

        row = record.raw_content
        title = self._text(row.get("CABECERA")) or f"Consulta {row.get('ID_CONSULTA', '')}".strip()

        sections = tuple(
            KnowledgeSectionData(kind=kind, content=text, position=index)
            for index, (column, kind) in enumerate(self.SECTION_MAP)
            if (text := self._text(row.get(column)))
        )
        attributes = tuple(
            KnowledgeAttributeData(name=name, value=text)
            for column, name in self.ATTRIBUTE_MAP
            if (text := self._text(row.get(column)))
        )

        item = KnowledgeItemData(
            kind="support_case",
            title=title,
            sections=sections,
            attributes=attributes,
            status="active",
            confidence=None,
        )
        locator = record.external_id
        excerpt = next((section.content for section in sections if section.kind == "solution"), None)
        return NormalizedKnowledge(
            items=(item,),
            evidence=EvidenceData(
                evidence_type="source_record",
                locator=locator,
                excerpt=excerpt,
                confidence=1.0,
            ),
        )
