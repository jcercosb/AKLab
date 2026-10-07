# ADR-0001 — Access is an adapter dependency, not a core dependency

## Status
Accepted for F0.2.

## Decision
The generic ingestion core consumes `SourceRecord` objects. A source adapter is responsible only for preserving and emitting source records; it does not create `KnowledgeItem` objects.

For Gredos SAT, Access reading sits behind `SatExtractor`. The first implementations may use:

- `mdbtools` (`mdb-export`) on macOS/Linux;
- an ODBC/ACE implementation on Windows;
- a neutral JSONL export produced by an external extractor.

The core never queries Access directly.

## Why
This makes `SAT.mdb` replaceable, keeps the engine product-independent, and lets us change the extraction technology without migrating the knowledge model.
