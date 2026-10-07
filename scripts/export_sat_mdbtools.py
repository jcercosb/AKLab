from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from applied_knowledge.adapters.gredos.sat.extractors import MdbToolsExtractor


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export selected SAT.mdb tables to neutral JSONL.")
    parser.add_argument("mdb", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tables", nargs="+", default=["CONSULTAS", "HISTORICO"])
    args = parser.parse_args()

    if shutil.which("mdb-export") is None:
        raise SystemExit("mdb-export not found; install mdbtools first")
    args.output.mkdir(parents=True, exist_ok=True)
    extractor = MdbToolsExtractor(args.mdb)
    counts: dict[str, int] = {}

    for table in args.tables:
        output = args.output / f"{table}.jsonl"
        count = 0
        with output.open("w", encoding="utf-8") as handle:
            for row in extractor.rows(table):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                count += 1
        counts[table] = count
        print(f"{table}: {count} rows -> {output}")

    manifest = {
        "source_file": args.mdb.name,
        "source_sha256": sha256(args.mdb),
        "tables": counts,
        "format": "jsonl",
        "extractor": "mdbtools/mdb-export",
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
