from __future__ import annotations

import argparse
import json
from pathlib import Path

from applied_knowledge.search import SearchService, SqliteFtsIndex
from applied_knowledge.storage.database import Database


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate classical search with Recall@K and MRR.")
    parser.add_argument("database", type=Path)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    cases = [
        json.loads(line)
        for line in args.dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        raise SystemExit("Evaluation dataset is empty")

    db = Database.sqlite_file(args.database)
    db.create_schema()
    recall_total = 0.0
    reciprocal_rank_total = 0.0

    with db.session() as session:
        SqliteFtsIndex(session).rebuild()
        search = SearchService(session)
        for index, case in enumerate(cases, 1):
            expected = set(case["expected_origin_keys"])
            mode = case.get("mode", "fts")
            common = dict(
                knowledge_space_id=case["knowledge_space_id"],
                kind=case.get("kind"),
                status=case.get("status", "active"),
                attribute_name=case.get("attribute_name"),
                attribute_value=case.get("attribute_value"),
                limit=args.k,
            )
            if mode == "exact":
                hits = search.exact(query=case.get("query"), **common)
            else:
                hits = search.fts(query=case["query"], **common)

            returned = [hit.origin_key for hit in hits]
            relevant = [position for position, key in enumerate(returned, 1) if key in expected]
            found = expected.intersection(returned)
            recall = len(found) / len(expected) if expected else 1.0
            rr = 1.0 / relevant[0] if relevant else 0.0
            recall_total += recall
            reciprocal_rank_total += rr
            print(
                f"case={index} mode={mode} recall@{args.k}={recall:.3f} "
                f"rr={rr:.3f} query={case.get('query')!r} top={returned[:3]}"
            )

    count = len(cases)
    print(f"cases={count}")
    print(f"mean_recall@{args.k}={recall_total / count:.3f}")
    print(f"mrr={reciprocal_rank_total / count:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
