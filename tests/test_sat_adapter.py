from pathlib import Path

from applied_knowledge.adapters.gredos.sat.adapter import GredosSatAdapter


class FakeExtractor:
    def rows(self, table: str):
        if table == "CONSULTAS":
            return iter([
                {"ID_CONSULTA": "7", "CABECERA": "Caso"},
            ])
        if table == "HISTORICO":
            return iter([
                {"ID_HISTORICO": "70", "ID_BOLETIN": "7", "DESCRIPCION": "Seguimiento"},
                {"ID_HISTORICO": "71", "ID_BOLETIN": "999", "DESCRIPCION": "Huerfano"},
            ])
        raise AssertionError(table)


def test_sat_adapter_preserves_history_as_source_items(tmp_path: Path) -> None:
    mdb = tmp_path / "SAT.mdb"
    mdb.write_bytes(b"sat-fixture")

    records = list(GredosSatAdapter(mdb, FakeExtractor()).records())

    assert [record.external_id for record in records] == [
        "CONSULTAS:7",
        "HISTORICO:70",
        "HISTORICO:71",
    ]
    assert records[0].parent_external_id is None
    assert records[1].parent_external_id == "CONSULTAS:7"
    assert records[2].parent_external_id == "CONSULTAS:999"
    assert records[1].metadata["table"] == "HISTORICO"
