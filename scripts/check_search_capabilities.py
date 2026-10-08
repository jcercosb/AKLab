from __future__ import annotations

import sqlite3


def main() -> int:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE capability_check USING fts5(content)")
        connection.execute("INSERT INTO capability_check(content) VALUES (?)", ("knowledge search",))
        found = connection.execute(
            "SELECT COUNT(*) FROM capability_check WHERE capability_check MATCH ?",
            ("knowledge",),
        ).fetchone()[0]
        if found != 1:
            raise RuntimeError("FTS5 table was created but search did not return the expected row")
        print(f"sqlite_version={sqlite3.sqlite_version}")
        print("fts5=available")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
