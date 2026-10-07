from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from applied_knowledge.domain.models import SourceRecord


class SatExtractor(Protocol):
    """Access-specific extraction boundary.

    It may be implemented with mdbtools on macOS/Linux, ODBC/ACE on Windows,
    or by consuming a previously generated neutral export.
    """

    def rows(self, table: str) -> Iterable[dict[str, Any]]: ...


class GredosSatAdapter:
    name = "gredos-sat"
    version = "0.2"

    def __init__(
        self,
        mdb_path: str | Path,
        extractor: SatExtractor,
        tables: tuple[str, ...] = ("CONSULTAS", "HISTORICO"),
    ) -> None:
        self.path = Path(mdb_path)
        self.extractor = extractor
        self.tables = tables

    def fingerprint(self) -> str | None:
        digest = hashlib.sha256()
        with self.path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def records(self) -> Iterable[SourceRecord]:
        if "CONSULTAS" in self.tables:
            for row in self.extractor.rows("CONSULTAS"):
                raw_id = row.get("ID_CONSULTA")
                if raw_id in (None, ""):
                    raise ValueError("CONSULTAS row without ID_CONSULTA")
                yield SourceRecord(
                    external_id=f"CONSULTAS:{raw_id}",
                    source_type="access_table_row",
                    raw_content=dict(row),
                    metadata={"table": "CONSULTAS", "primary_key": "ID_CONSULTA"},
                )

        if "HISTORICO" in self.tables:
            for row in self.extractor.rows("HISTORICO"):
                raw_id = row.get("ID_HISTORICO")
                if raw_id in (None, ""):
                    raise ValueError("HISTORICO row without ID_HISTORICO")
                bulletin_id = row.get("ID_BOLETIN")
                parent_external_id = None
                if bulletin_id not in (None, ""):
                    parent_external_id = f"CONSULTAS:{bulletin_id}"
                yield SourceRecord(
                    external_id=f"HISTORICO:{raw_id}",
                    source_type="access_table_row",
                    raw_content=dict(row),
                    metadata={
                        "table": "HISTORICO",
                        "primary_key": "ID_HISTORICO",
                        "parent_key": "ID_BOLETIN",
                    },
                    parent_external_id=parent_external_id,
                )
