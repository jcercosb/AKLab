from __future__ import annotations

import argparse
from pathlib import Path

from applied_knowledge.search import SqliteFtsIndex
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.repository import KnowledgeRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the SQLite FTS5 search index.")
    parser.add_argument("database", type=Path)
    parser.add_argument("--space", dest="knowledge_space_id")
    args = parser.parse_args()

    db = Database.sqlite_file(args.database)
    db.create_schema()
    with db.session() as session:
        if args.knowledge_space_id is not None:
            repo = KnowledgeRepository(session)
            if repo.get_space(args.knowledge_space_id) is None:
                raise SystemExit(f"KnowledgeSpace not found: {args.knowledge_space_id}")
        count = SqliteFtsIndex(session).rebuild(
            knowledge_space_id=args.knowledge_space_id
        )
        print(f"indexed={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
