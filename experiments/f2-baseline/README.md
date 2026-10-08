# F2 classical-search baseline

This folder starts the evaluation corpus for retrieval experiments.

`gredos-seed.jsonl` is intentionally small. Its purpose is to prove the evaluation loop before building a larger human-reviewed dataset.

Each JSONL row contains a query and one or more expected stable `origin_key` values. The evaluator reports Recall@K and MRR.

Run against a database containing the full SAT import:

    python scripts/evaluate_search_baseline.py data/generated/aklab-f0.2.sqlite experiments/f2-baseline/gredos-seed.jsonl --k 5

The dataset should grow during F2 with real questions, synonyms, vague wording and cases where lexical search is expected to fail. Those failures become valuable baselines for later embeddings, hybrid retrieval and reranking experiments.
