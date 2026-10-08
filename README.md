# Applied Knowledge Lab

Applied Knowledge Lab is a generic technical knowledge system and an applied-AI learning laboratory. Gredos ERP / `SAT.mdb` is the first real source, not the internal data model.

## Current milestone

F1 proves that AKLab can start from an empty knowledge space and be populated manually, independently of Gredos or SAT.

F0.2 established the source/knowledge/evidence boundary and a reproducible, idempotent SAT ingestion path. F1 now adds manual knowledge CRUD and revision history without introducing an LLM.

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
                  Evidence
                     |
             KnowledgeRevision
```

Imported SAT knowledge and manually maintained knowledge share the canonical model, but imported knowledge cannot be modified through the manual-edit path.

See:

- `docs/F0.2-status.md`
- `docs/F1-status.md`
- `docs/adr/0001-source-boundary.md`
- `docs/adr/0002-knowledge-confidence-semantics.md`
- `docs/adr/0003-sat-history-source-items.md`
- `docs/adr/0004-manual-knowledge-provenance-and-revisions.md`

## Install

```bash
python -m pip install -e '.[dev]'
```

## Tests

```bash
python -m pytest -q
```

## Run the API

```bash
AKLAB_DATABASE_URL=sqlite:///data/generated/aklab.sqlite \
python -m uvicorn applied_knowledge.api.app:create_app --factory --reload
```

Open `/docs` for FastAPI's interactive API documentation.

## SAT neutral export

With `mdbtools` installed:

```bash
python scripts/export_sat_mdbtools.py /path/to/SAT.mdb data/generated/sat-export
python scripts/import_sat_neutral.py /path/to/SAT.mdb data/generated/sat-export data/generated/knowledge.sqlite
python scripts/inspect_f0_store.py data/generated/knowledge.sqlite
```

The two-step flow is intentional: Microsoft Access is an adapter concern, not a runtime dependency of the knowledge core.
