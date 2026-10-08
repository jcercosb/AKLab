from __future__ import annotations

from sqlalchemy import func, select

from applied_knowledge.domain.models import (
    KnowledgeAttributeData,
    KnowledgeItemData,
    KnowledgeSectionData,
)
from applied_knowledge.knowledge import (
    KnowledgeNotManualError,
    ManualKnowledgeService,
    manual_source_id,
)
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.models import (
    EvidenceRow,
    KnowledgeItemRow,
    KnowledgeRevisionRow,
    SourceItemRow,
    SourceRow,
)
from applied_knowledge.storage.repository import KnowledgeRepository


def _item(title: str = "TIMEOUT_API") -> KnowledgeItemData:
    return KnowledgeItemData(
        kind="parameter",
        title=title,
        content="Controls the maximum API wait time.",
        sections=(
            KnowledgeSectionData(
                kind="procedure",
                content="Check the parameter before investigating E102.",
            ),
        ),
        attributes=(
            KnowledgeAttributeData(name="recommended_value", value="30", value_type="integer"),
        ),
    )


def test_manual_create_preserves_source_and_evidence() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()

    with db.session() as session:
        repo = KnowledgeRepository(session)
        repo.ensure_space(id="demo", name="Demo product")
        service = ManualKnowledgeService(repo)

        row = service.create(knowledge_space_id="demo", item=_item())

        assert row.kind == "parameter"
        assert row.title == "TIMEOUT_API"
        assert row.status == "active"
        assert row.confidence is None
        assert session.scalar(select(func.count()).select_from(KnowledgeItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(SourceItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(EvidenceRow)) == 1
        assert session.scalar(select(func.count()).select_from(KnowledgeRevisionRow)) == 1

        source = session.get(SourceRow, manual_source_id("demo"))
        assert source is not None
        assert source.type == "manual"

        source_item = session.scalar(select(SourceItemRow))
        assert source_item is not None
        assert source_item.external_id.startswith("MANUAL:")
        assert source_item.raw_content["title"] == "TIMEOUT_API"
        assert source_item.last_seen_run_id is None

        evidence = session.scalar(select(EvidenceRow))
        assert evidence is not None
        assert evidence.evidence_type == "manual_entry"
        assert evidence.source_item_id == source_item.id
        assert evidence.confidence == 1.0


def test_manual_update_reuses_identity_and_archive_is_logical_delete() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()

    with db.session() as session:
        repo = KnowledgeRepository(session)
        repo.ensure_space(id="demo", name="Demo product")
        service = ManualKnowledgeService(repo)
        created = service.create(knowledge_space_id="demo", item=_item())
        created_id = created.id

        updated = service.update(
            knowledge_space_id="demo",
            knowledge_item_id=created_id,
            changes={
                "title": "TIMEOUT_API revised",
                "attributes": (
                    KnowledgeAttributeData(
                        name="recommended_value",
                        value="45",
                        value_type="integer",
                    ),
                ),
            },
        )

        assert updated.id == created_id
        assert updated.title == "TIMEOUT_API revised"
        assert updated.attributes[0].value == "45"
        assert session.scalar(select(func.count()).select_from(KnowledgeItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(SourceItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(EvidenceRow)) == 1

        archived = service.archive(
            knowledge_space_id="demo",
            knowledge_item_id=created_id,
        )
        assert archived.status == "archived"
        assert service.list(knowledge_space_id="demo") == []
        assert len(service.list(knowledge_space_id="demo", status=None)) == 1

        revisions = repo.list_knowledge_revisions(knowledge_item_id=created_id)
        assert [revision.revision for revision in revisions] == [1, 2, 3]
        assert revisions[0].snapshot["title"] == "TIMEOUT_API"
        assert revisions[1].snapshot["title"] == "TIMEOUT_API revised"
        assert revisions[2].snapshot["status"] == "archived"


def test_manual_service_rejects_update_of_imported_knowledge() -> None:
    from applied_knowledge.domain.models import SourceRecord

    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()

    with db.session() as session:
        repo = KnowledgeRepository(session)
        repo.ensure_space(id="gredos", name="Gredos ERP")
        repo.ensure_source(
            id="gredos-sat",
            knowledge_space_id="gredos",
            type="access_database",
            name="SAT.mdb",
        )
        source_item = repo.upsert_source_item(
            source_id="gredos-sat",
            record=SourceRecord(
                external_id="CONSULTAS:1",
                source_type="access_table_row",
                raw_content={"ID_CONSULTA": "1", "CABECERA": "Imported"},
            ),
        ).row
        imported = repo.upsert_normalized_item(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            source_item=source_item,
            item_index=0,
            item=KnowledgeItemData(kind="support_case", title="Imported"),
            evidence_type="source_record",
            evidence_locator="CONSULTAS:1",
            evidence_excerpt="Imported",
            evidence_confidence=1.0,
        )

        service = ManualKnowledgeService(repo)
        try:
            service.update(
                knowledge_space_id="gredos",
                knowledge_item_id=imported.id,
                changes={"title": "Do not mutate SAT"},
            )
        except KnowledgeNotManualError:
            pass
        else:
            raise AssertionError("Imported knowledge must not be editable as manual knowledge")
