# Applied Knowledge Lab

Applied Knowledge Lab is a generic technical knowledge system and an applied-AI learning laboratory. Gredos ERP / `SAT.mdb` is the first real source, not the internal data model.

## F0.2-A

This bootstrap deliberately contains no LLM. It establishes the source/knowledge/evidence boundary and a reproducible idempotent ingestion path before AI techniques are added.

### Run tests

```bash
python -m pytest -q
```

### Architectural boundary

```text
external source
    -> SourceAdapter
    -> SourceRecord
    -> generic Importer
    -> SourceItem
    -> KnowledgeNormalizer
    -> KnowledgeItem + Evidence
```

`SourceAdapter` does not create knowledge. `SAT.mdb` is isolated behind the Gredos SAT adapter/extractor boundary.

See `docs/F0.2-status.md` and `docs/adr/0001-source-boundary.md`.

### F0.2-B local extraction workflow

When `mdbtools` is available, export Access into a neutral format first:

```bash
python scripts/export_sat_mdbtools.py /path/to/SAT.mdb data/generated/sat-export
python scripts/import_sat_neutral.py /path/to/SAT.mdb data/generated/sat-export data/generated/knowledge.sqlite
```

This two-step flow is intentional: the knowledge core can be tested and reused without retaining Microsoft Access as a runtime dependency.
