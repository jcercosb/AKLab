from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class KnowledgeSpaceRow(Base):
    __tablename__ = "knowledge_spaces"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    knowledge_space_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImportRunRow(Base):
    __tablename__ = "import_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    adapter: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_fingerprint: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SourceItemRow(Base):
    __tablename__ = "source_items"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_external_id: Mapped[str | None] = mapped_column(String(500), index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_run_id: Mapped[str | None] = mapped_column(ForeignKey("import_runs.id"))


class KnowledgeItemRow(Base):
    __tablename__ = "knowledge_items"
    __table_args__ = (
        UniqueConstraint("knowledge_space_id", "origin_key", name="uq_knowledge_origin"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_space_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_key: Mapped[str] = mapped_column(String(700), nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active")
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sections: Mapped[list["KnowledgeSectionRow"]] = relationship(
        back_populates="knowledge_item", cascade="all, delete-orphan"
    )
    attributes: Mapped[list["KnowledgeAttributeRow"]] = relationship(
        back_populates="knowledge_item", cascade="all, delete-orphan"
    )


class KnowledgeSectionRow(Base):
    __tablename__ = "knowledge_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_item_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    knowledge_item: Mapped[KnowledgeItemRow] = relationship(back_populates="sections")


class KnowledgeAttributeRow(Base):
    __tablename__ = "knowledge_attributes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_item_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    knowledge_item: Mapped[KnowledgeItemRow] = relationship(back_populates="attributes")


class EvidenceRow(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("knowledge_item_id", "source_item_id", "evidence_type", name="uq_evidence_link"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_item_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_item_id: Mapped[str] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    locator: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
