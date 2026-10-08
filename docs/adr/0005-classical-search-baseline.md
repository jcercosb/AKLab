# ADR-0005 - Classical search is the retrieval baseline

## Status

Accepted in F2.

## Context

AKLab is intended to compare AI retrieval techniques against simpler alternatives rather than assuming that semantic search is automatically superior.

Before embeddings or RAG, the system needs a reproducible lexical baseline over the same canonical knowledge store.

The canonical model must remain independent of any particular retrieval representation. Search indexes are derived data and must be rebuildable.

## Decision

F2 introduces two classical retrieval paths.

`exact` uses canonical SQL data directly. It supports exact title/origin matching and structured filters such as `kind`, `status`, attribute name and attribute value.

`fts` uses SQLite FTS5 with BM25 ranking. The FTS document is a derived projection of:

- title;
- summary;
- content;
- sections;
- attributes.

Title and attribute terms receive stronger BM25 weights than general body text.

The FTS table is not canonical knowledge. It can be deleted and rebuilt from `KnowledgeItem`, `KnowledgeSection` and `KnowledgeAttribute` without losing information.

Manual CRUD updates the index immediately when the API path is used. Imports may also update it while normalizing. A full rebuild command remains available so index correctness never depends on historical side effects.

## Query semantics

The FTS baseline deliberately remains simple.

Input is tokenized into Unicode word tokens and combined with OR. SQLite's `unicode61` tokenizer removes diacritics for matching. No stemming, synonym expansion, LLM rewriting or semantic similarity is introduced in F2.

These limitations are intentional. Their failures will become evidence for later techniques.

## Evaluation

F2 starts a small human-reviewed retrieval dataset using stable `origin_key` identifiers. The evaluator reports:

- Recall@K;
- reciprocal rank per case;
- mean reciprocal rank (MRR).

The initial dataset is only a seed. It must grow with realistic and difficult questions before comparing embeddings or hybrid retrieval.

## Consequences

AKLab now has a measurable retrieval baseline before AI retrieval is introduced.

A lexical failure is not automatically a defect. It can be a useful experimental result demonstrating a class of queries that later techniques may improve.
