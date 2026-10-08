# Applied Knowledge Lab

Applied Knowledge Lab is a generic technical knowledge system and an applied-AI learning laboratory. Gredos ERP / `SAT.mdb` is the first real source, not the internal data model.

## Current milestone

F2 establishes the first retrieval baseline before embeddings or RAG.

F0.2 established the source/knowledge/evidence boundary and reproducible SAT ingestion. F1 proved that AKLab can start empty and be populated manually. F2 now retrieves that same canonical knowledge through exact structured SQL and SQLite FTS5/BM25.

```text
external source                 human input
      |                              |
SourceAdapter                     FastAPI
      |                              |
SourceItem                 ManualKnowledgeService
      |                              |
normalizer                   manual SourceItem
      |                              |
      +--------> KnowledgeItem <-----+
                     |
          +----------+-----------+
          |                      |
      Evidence            derived retrieval
                                 |
                         exact SQL / filters
                                 |
                           FTS5 + BM25
```

The search index is derived data. It can be rebuilt from canonical knowledge and is never treated as the source of truth.

See:

- `docs/F0.2-status.md`
- `docs/F1-status.md`
- `docs/F2-status.md`
- `docs/adr/0001-source-boundary.md`
- `docs/adr/0002-knowledge-confidence-semantics.md`
- `docs/adr/0003-sat-history-source-items.md`
- `docs/adr/0004-manual-knowledge-provenance-and-revisions.md`
- `docs/adr/0005-classical-search-baseline.md`

## Install

```bash
python -m pip install -e '.[dev]'
```

## Tests

```bash
python -m pytest -q
```

## Search capability check

```bash
python scripts/check_search_capabilities.py
```

## Run the API

```bash
AKLAB_DATABASE_URL=sqlite:///data/generated/aklab.sqlite \
python -m uvicorn applied_knowledge.api.app:create_app --factory --reload
```

Open `/docs` for FastAPI's interactive API documentation.

Classical retrieval is exposed through:

```text
GET /knowledge-spaces/{knowledge_space_id}/search?mode=fts&q=...
GET /knowledge-spaces/{knowledge_space_id}/search?mode=exact&...
POST /knowledge-spaces/{knowledge_space_id}/search-index/rebuild
```

## SAT neutral export

With `mdbtools` installed:

```bash
python scripts/export_sat_mdbtools.py /path/to/SAT.mdb data/generated/sat-export
python scripts/import_sat_neutral.py /path/to/SAT.mdb data/generated/sat-export data/generated/knowledge.sqlite
python scripts/inspect_f0_store.py data/generated/knowledge.sqlite
```

The two-step flow is intentional: Microsoft Access is an adapter concern, not a runtime dependency of the knowledge core.

## Rebuild the search index

```bash
python scripts/rebuild_search_index.py data/generated/knowledge.sqlite --space gredos
```

## Evaluate the F2 lexical baseline

```bash
python scripts/evaluate_search_baseline.py \
  data/generated/knowledge.sqlite \
  experiments/f2-baseline/gredos-seed.jsonl \
  --k 5
```

The initial evaluation dataset is only a seed. Expand it with real, difficult questions before drawing conclusions or comparing F2 against embeddings and hybrid retrieval.
