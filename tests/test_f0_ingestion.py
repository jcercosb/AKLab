from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select

from applied_knowledge.adapters.gredos.sat.normalizer import GredosSatNormalizer
from applied_knowledge.domain.models import SourceRecord
from applied_knowledge.ingestion.importer import Importer
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.models import EvidenceRow, KnowledgeItemRow, SourceItemRow
from applied_knowledge.storage.repository import KnowledgeRepository


class FakeSatAdapter:
    name = "test-sat"
    version = "1"

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def fingerprint(self) -> str:
        return "fake-fingerprint"

    def records(self) -> Iterable[SourceRecord]:
        for row in self.rows:
            yield SourceRecord(
                external_id=f"CONSULTAS:{row['ID_CONSULTA']}",
                source_type="access_table_row",
                raw_content=row,
                metadata={"table": "CONSULTAS"},
            )


def _bootstrap(repo: KnowledgeRepository) -> None:
    repo.ensure_space(id="gredos", name="Gredos ERP")
    repo.ensure_source(
        id="gredos-sat",
        knowledge_space_id="gredos",
        type="access_database",
        name="SAT.mdb",
    )


def test_import_is_idempotent_and_traceable() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    rows = [
        {
            "ID_CONSULTA": 1234,
            "CABECERA": "Error al facturar",
            "PROGRAMA": "GESTION",
            "MODULO": "FACTURACION",
            "SINTOMAS": "No permite facturar",
            "ENTORNO": "Cliente demo",
            "SOLUCION": "Revisar parametro X",
            "OBSERVACIONES": "Caso de prueba",
        },
        {
            "ID_CONSULTA": 1235,
            "CABECERA": "Impresion",
            "PROGRAMA": "GESTION",
            "MODULO": "IMPRESION",
            "SINTOMAS": "No imprime",
            "SOLUCION": "Comprobar dispositivo",
        },
    ]

    with db.session() as session:
        repo = KnowledgeRepository(session)
        _bootstrap(repo)
        importer = Importer(repo)
        first = importer.run(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            adapter=FakeSatAdapter(rows),
            normalizer=GredosSatNormalizer(),
        )
        second = importer.run(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            adapter=FakeSatAdapter(rows),
            normalizer=GredosSatNormalizer(),
        )

        assert first.new == 2
        assert first.knowledge_items == 2
        assert second.unchanged == 2
        assert second.knowledge_items == 0
        assert session.scalar(select(func.count()).select_from(SourceItemRow)) == 2
        assert session.scalar(select(func.count()).select_from(KnowledgeItemRow)) == 2
        assert session.scalar(select(func.count()).select_from(EvidenceRow)) == 2


def test_changed_record_updates_without_duplication() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    first_row = {"ID_CONSULTA": 7, "CABECERA": "Original", "SOLUCION": "A"}
    changed_row = {"ID_CONSULTA": 7, "CABECERA": "Original", "SOLUCION": "B"}

    with db.session() as session:
        repo = KnowledgeRepository(session)
        _bootstrap(repo)
        importer = Importer(repo)
        importer.run(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            adapter=FakeSatAdapter([first_row]),
            normalizer=GredosSatNormalizer(),
        )
        result = importer.run(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            adapter=FakeSatAdapter([changed_row]),
            normalizer=GredosSatNormalizer(),
        )

        assert result.changed == 1
        assert session.scalar(select(func.count()).select_from(SourceItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(KnowledgeItemRow)) == 1
        assert session.scalar(select(func.count()).select_from(EvidenceRow)) == 1
