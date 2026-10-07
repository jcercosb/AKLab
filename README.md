# Applied Knowledge Lab

Applied Knowledge Lab is a generic technical knowledge system and an applied-AI learning laboratory. Gredos ERP / `SAT.mdb` is the first real source, not the internal data model.

## Current milestone

F0.2 establishes the source/knowledge/evidence boundary and a reproducible, idempotent SAT ingestion path before any LLM or retrieval technique is added.

```text
external source
    -> SourceAdapter
    -> SourceRecord
    -> generic Importer
    -> SourceItem
    -> KnowledgeNormalizer
    -> KnowledgeItem + Evidence
```

`SourceAdapter` never creates knowledge directly. `SAT.mdb` is isolated behind the Gredos SAT adapter/extractor boundary.

`CONSULTAS` is deterministically normalized into initial `support_case` knowledge. `HISTORICO` is preserved as independent source material with `parent_external_id` back to its consultation when available, but is not automatically promoted to knowledge.

See:

- `docs/F0.2-status.md`
- `docs/adr/0001-source-boundary.md`
- `docs/adr/0002-knowledge-confidence-semantics.md`
- `docs/adr/0003-sat-history-source-items.md`

## Tests

```bash
python -m pytest -q
```

## SAT neutral export

With `mdbtools` installed:

```bash
python scripts/export_sat_mdbtools.py /path/to/SAT.mdb data/generated/sat-export
python scripts/import_sat_neutral.py /path/to/SAT.mdb data/generated/sat-export data/generated/knowledge.sqlite
python scripts/inspect_f0_store.py data/generated/knowledge.sqlite
```

The two-step flow is intentional: Microsoft Access is an adapter concern, not a runtime dependency of the knowledge core.
