from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class MdbToolsExtractor:
    """Read Access through the mdbtools command line.

    This dependency belongs to the adapter boundary, not to the core.
    """

    def __init__(self, mdb_path: str | Path) -> None:
        self.path = Path(mdb_path)

    @staticmethod
    def available() -> bool:
        return shutil.which("mdb-export") is not None

    def rows(self, table: str) -> Iterable[dict[str, Any]]:
        if not self.available():
            raise RuntimeError(
                "mdb-export is not installed. Install mdbtools or use NeutralJsonlExtractor."
            )
        # Use an explicit control-character sentinel so NULL remains
        # distinguishable from an empty string in the neutral representation.
        null_sentinel = "\x1f"

        completed = subprocess.run(
            ["mdb-export", "-0", null_sentinel, str(self.path), table],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )

        for row in csv.DictReader(io.StringIO(completed.stdout)):
            yield {
                key: None if value == null_sentinel else value
                for key, value in row.items()
            }


class NeutralJsonlExtractor:
    """Consume a portable JSONL export independent of Microsoft Access."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def rows(self, table: str) -> Iterable[dict[str, Any]]:
        path = self.directory / f"{table}.jsonl"
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError(f"Expected JSON object in {path}")
                    yield value
