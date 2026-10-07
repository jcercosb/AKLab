from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def scalar(con: sqlite3.Connection, sql: str) -> int:
    value = con.execute(sql).fetchone()
    if value is None:
        return 0
    return int(value[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect an F0 AKLab SQLite store.")
    parser.add_argument("database", type=Path)
    args = parser.parse_args()

    con = sqlite3.connect(args.database)

    print("import_runs", scalar(con, "SELECT COUNT(*) FROM import_runs"))
    print("source_items", scalar(con, "SELECT COUNT(*) FROM source_items"))
    print(
        "consultas_source_items",
        scalar(con, "SELECT COUNT(*) FROM source_items WHERE external_id LIKE 'CONSULTAS:%'"),
    )
    print(
        "historico_source_items",
        scalar(con, "SELECT COUNT(*) FROM source_items WHERE external_id LIKE 'HISTORICO:%'"),
    )
    print("knowledge_items", scalar(con, "SELECT COUNT(*) FROM knowledge_items"))
    print("evidence", scalar(con, "SELECT COUNT(*) FROM evidence"))
    print(
        "historico_orphans",
        scalar(
            con,
            """
            SELECT COUNT(*)
            FROM source_items h
            WHERE h.external_id LIKE 'HISTORICO:%'
              AND h.parent_external_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM source_items p
                  WHERE p.source_id = h.source_id
                    AND p.external_id = h.parent_external_id
              )
            """,
        ),
    )

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
