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
    version = "0.1"

    def __init__(self, mdb_path: str | Path, extractor: SatExtractor) -> None:
        self.path = Path(mdb_path)
        self.extractor = extractor

    def fingerprint(self) -> str | None:
        digest = hashlib.sha256()
        with self.path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def records(self) -> Iterable[SourceRecord]:
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
