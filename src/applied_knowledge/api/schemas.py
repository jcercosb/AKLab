from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from applied_knowledge.domain.models import (
    KnowledgeAttributeData,
    KnowledgeItemData,
    KnowledgeSectionData,
)
from applied_knowledge.storage.models import KnowledgeItemRow, KnowledgeSpaceRow


class KnowledgeSpaceCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSpaceView(BaseModel):
    id: str
    name: str
    description: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_row(cls, row: KnowledgeSpaceRow) -> "KnowledgeSpaceView":
        return cls(
            id=row.id,
            name=row.name,
            description=row.description,
            metadata=row.metadata_json or {},
        )


class SectionInput(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    title: str | None = None
    content: str = Field(min_length=1)
    position: int = 0

    def to_domain(self) -> KnowledgeSectionData:
        return KnowledgeSectionData(**self.model_dump())


class AttributeInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    value: str
    value_type: str = "string"

    def to_domain(self) -> KnowledgeAttributeData:
        return KnowledgeAttributeData(**self.model_dump())


class KnowledgeCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = None
    content: str | None = None
    sections: list[SectionInput] = Field(default_factory=list)
    attributes: list[AttributeInput] = Field(default_factory=list)

    def to_domain(self) -> KnowledgeItemData:
        return KnowledgeItemData(
            kind=self.kind,
            title=self.title,
            summary=self.summary,
            content=self.content,
            status="active",
            confidence=None,
            sections=tuple(value.to_domain() for value in self.sections),
            attributes=tuple(value.to_domain() for value in self.attributes),
        )


class KnowledgePatch(BaseModel):
    kind: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = None
    content: str | None = None
    status: Literal["active", "deprecated", "archived"] | None = None
    sections: list[SectionInput] | None = None
    attributes: list[AttributeInput] | None = None

    def to_changes(self) -> dict[str, object]:
        raw = self.model_dump(exclude_unset=True)
        if raw.get("sections") is not None:
            raw["sections"] = tuple(
                KnowledgeSectionData(**value) for value in raw["sections"]
            )
        elif "sections" in raw:
            raw.pop("sections")
        if raw.get("attributes") is not None:
            raw["attributes"] = tuple(
                KnowledgeAttributeData(**value) for value in raw["attributes"]
            )
        elif "attributes" in raw:
            raw.pop("attributes")
        return raw


class SectionView(BaseModel):
    kind: str
    title: str | None
    content: str
    position: int


class AttributeView(BaseModel):
    name: str
    value: str
    value_type: str


class KnowledgeView(BaseModel):
    id: str
    knowledge_space_id: str
    kind: str
    title: str
    summary: str | None
    content: str | None
    status: str
    confidence: float | None
    sections: list[SectionView]
    attributes: list[AttributeView]

    @classmethod
    def from_row(cls, row: KnowledgeItemRow) -> "KnowledgeView":
        return cls(
            id=row.id,
            knowledge_space_id=row.knowledge_space_id,
            kind=row.kind,
            title=row.title,
            summary=row.summary,
            content=row.content,
            status=row.status,
            confidence=row.confidence,
            sections=[
                SectionView(
                    kind=value.kind,
                    title=value.title,
                    content=value.content,
                    position=value.position,
                )
                for value in sorted(row.sections, key=lambda item: item.position)
            ],
            attributes=[
                AttributeView(
                    name=value.name,
                    value=value.value,
                    value_type=value.value_type,
                )
                for value in sorted(row.attributes, key=lambda item: (item.name, item.value))
            ],
        )


class KnowledgeRevisionView(BaseModel):
    revision: int
    snapshot: dict[str, Any]
    author_type: str
    created_at: str
