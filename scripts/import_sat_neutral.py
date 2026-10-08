from __future__ import annotations

import argparse
from pathlib import Path

from applied_knowledge.adapters.gredos.sat.adapter import GredosSatAdapter
from applied_knowledge.adapters.gredos.sat.extractors import NeutralJsonlExtractor
from applied_knowledge.adapters.gredos.sat.normalizer import GredosSatNormalizer
from applied_knowledge.ingestion.importer import Importer
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.repository import KnowledgeRepository
from applied_knowledge.search import SqliteFtsIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a neutral SAT JSONL export into the F0 knowledge store.")
    parser.add_argument("mdb", type=Path, help="Original SAT.mdb, used only for source fingerprint")
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()

    db = Database.sqlite_file(args.database)
    db.create_schema()
    extractor = NeutralJsonlExtractor(args.export_dir)
    adapter = GredosSatAdapter(args.mdb, extractor)

    with db.session() as session:
        repo = KnowledgeRepository(session)
        search_index = SqliteFtsIndex(session)
        repo.ensure_space(id="gredos", name="Gredos ERP")
        repo.ensure_source(
            id="gredos-sat",
            knowledge_space_id="gredos",
            type="access_database",
            name="SAT.mdb",
        )
        result = Importer(repo, search_index=search_index).run(
            knowledge_space_id="gredos",
            source_id="gredos-sat",
            adapter=adapter,
            normalizer=GredosSatNormalizer(),
        )
        indexed = search_index.rebuild(knowledge_space_id="gredos")
        print(result)
        print(f"search_indexed={indexed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
