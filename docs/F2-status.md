# F2 - Classical search baseline

## Goal

Establish a non-AI retrieval baseline before embeddings and RAG.

F2 answers a fundamental experimental question: how far can AKLab get with exact structured retrieval and lexical full-text ranking alone?

## Implemented

### Exact SQL retrieval

The search service can retrieve canonical `KnowledgeItem` data using:

- exact query against title, origin key or attribute value;
- `kind` filter;
- `status` filter;
- exact attribute-name filter;
- exact attribute-value filter;
- result limit.

This path does not depend on the FTS index.

### SQLite FTS5 + BM25

AKLab now maintains a rebuildable SQLite FTS5 index over normalized knowledge.

Indexed text includes:

- title;
- summary;
- content;
- section titles and content;
- attribute names and values.

The BM25 weighting favors title and structured attributes while still considering general text.

The index is derived representation, not knowledge. It can be rebuilt from the canonical store at any time.

### Index lifecycle

Manual creation and editing through `ManualKnowledgeService` can update FTS immediately.

The SAT import path can update FTS while normalized knowledge is written and performs a final rebuild to make upgrading an existing database safe even when all source rows are `unchanged`.

The API rebuilds the derived index when it starts and also exposes an explicit per-space rebuild endpoint.

### API

New endpoint:

`GET /knowledge-spaces/{knowledge_space_id}/search`

Modes:

- `mode=exact`
- `mode=fts`

Common filters include `kind`, archive inclusion, attribute name/value and result limit.

Explicit rebuild:

`POST /knowledge-spaces/{knowledge_space_id}/search-index/rebuild`

### Evaluation

`experiments/f2-baseline/gredos-seed.jsonl` starts a small evaluation corpus with five real SAT cases already inspected during F0.2.

`scripts/evaluate_search_baseline.py` measures Recall@K and MRR using stable `origin_key` values.

This dataset is intentionally too small for final conclusions. Its purpose is to validate the measurement loop before expanding it with harder real questions.

### Capability check

`scripts/check_search_capabilities.py` verifies that the Python SQLite build supports FTS5.

## Important limitations

F2 intentionally does not implement:

- stemming;
- synonyms;
- embeddings;
- vector search;
- query rewriting;
- multi-query retrieval;
- reranking;
- RAG;
- LLM interpretation.

For example, lexical variants such as `facturar` and `facturacion` may not behave as a semantic user expects. Such failures are part of the baseline, not something to hide before later experiments.

## Verification

The focused suite now covers:

- exact matching;
- structured attribute filtering;
- FTS search through title, sections and attributes;
- automatic index refresh after manual edit;
- archived-item filtering;
- rebuilding a missing derived index;
- API search and explicit rebuild;
- importer-to-FTS integration.

Expected suite status after F2 package application:

`16 passed`

## Real SAT validation

Validated on the real SAT corpus on 2026-10-08:

- SQLite 3.38.4 with FTS5 available;
- 13,618 SourceItems imported;
- 3,249 KnowledgeItems normalized and indexed;
- second import: 13,618 unchanged, 0 new KnowledgeItems;
- five seed evaluation cases;
- mean Recall@5 = 1.000;
- MRR = 1.000;
- expected KnowledgeItem ranked Top-1 in all five seed cases.

These metrics validate the end-to-end baseline and evaluation loop. They are not evidence that BM25 is sufficient for the full domain: the seed queries intentionally use vocabulary close to the source text and must be expanded with paraphrases, synonyms, vague wording and adversarial cases before comparing later retrieval techniques.

## Next after F2

Before moving to structured LLM interpretation in F3, expand the evaluation dataset with realistic questions that include:

- exact identifiers;
- normal vocabulary;
- synonyms;
- vague wording;
- spelling variants;
- cases where the answer exists but shares few literal words with the question.

That expanded baseline will make the later embeddings comparison meaningful rather than anecdotal.
