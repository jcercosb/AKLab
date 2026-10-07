from applied_knowledge.adapters.gredos.sat.normalizer import GredosSatNormalizer
from applied_knowledge.domain.models import SourceRecord


def test_sat_mapping_is_deterministic_and_only_maps_present_fields() -> None:
    record = SourceRecord(
        external_id="CONSULTAS:42",
        source_type="access_table_row",
        raw_content={
            "ID_CONSULTA": 42,
            "CABECERA": "Problema de ejemplo",
            "PROGRAMA": "GESTION",
            "MODULO": "VENTAS",
            "SINTOMAS": "Sintoma",
            "ENTORNO": "",
            "SOLUCION": "Solucion",
            "OBSERVACIONES": None,
        },
    )
    result = GredosSatNormalizer().normalize(record)
    item = result.items[0]

    assert item.kind == "support_case"
    assert item.title == "Problema de ejemplo"
    assert item.status == "active"
    assert item.confidence is None
    assert result.evidence.confidence == 1.0
    assert [(s.kind, s.content) for s in item.sections] == [
        ("symptom", "Sintoma"),
        ("solution", "Solucion"),
    ]
    assert [(a.name, a.value) for a in item.attributes] == [
        ("program", "GESTION"),
        ("module", "VENTAS"),
    ]
    assert result.evidence.locator == "CONSULTAS:42"


def test_sat_history_is_not_normalized_into_knowledge() -> None:
    record = SourceRecord(
        external_id="HISTORICO:70",
        source_type="access_table_row",
        raw_content={
            "ID_HISTORICO": "70",
            "ID_BOLETIN": "7",
            "DESCRIPCION": "Cambio de responsable",
        },
        metadata={"table": "HISTORICO"},
        parent_external_id="CONSULTAS:7",
    )

    result = GredosSatNormalizer().normalize(record)

    assert result.items == ()
