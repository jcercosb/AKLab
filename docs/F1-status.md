# F1 - Manual knowledge CRUD

## Goal

Prove that Applied Knowledge Lab can start with an empty knowledge space and become useful without SAT, Gredos or any external source.

F1 deliberately contains no LLM functionality. Manual knowledge creation is the baseline that later AI-assisted ingestion must improve rather than replace.

## Implemented

- Create and list `KnowledgeSpace` objects through the API.
- Create manual `KnowledgeItem` objects from scratch.
- Store sections and structured attributes.
- Read individual items and list knowledge by space and kind.
- Patch manually maintained knowledge.
- Archive knowledge through logical deletion.
- Preserve manual provenance through a dedicated `Source` and `SourceItem`.
- Link manual knowledge to evidence of type `manual_entry`.
- Record a `KnowledgeRevision` snapshot for creation, every edit and archival.
- Reject attempts to edit imported SAT knowledge through the manual-edit path.
- Provide a FastAPI interface while keeping the application service independent from HTTP.

## F1 flow

```text
human input
    -> FastAPI
    -> ManualKnowledgeService
    -> manual Source
    -> manual SourceItem
    -> KnowledgeItem
    -> Evidence
    -> KnowledgeRevision
```

## API surface

```text
GET    /health
POST   /knowledge-spaces
GET    /knowledge-spaces
POST   /knowledge-spaces/{space}/knowledge
GET    /knowledge-spaces/{space}/knowledge
GET    /knowledge-spaces/{space}/knowledge/{item}
PATCH  /knowledge-spaces/{space}/knowledge/{item}
DELETE /knowledge-spaces/{space}/knowledge/{item}
GET    /knowledge-spaces/{space}/knowledge/{item}/revisions
```

`DELETE` archives the item; it does not physically remove evidence or history.

## Run locally

Install/update dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run the API:

```bash
AKLAB_DATABASE_URL=sqlite:///data/generated/aklab.sqlite \
python -m uvicorn applied_knowledge.api.app:create_app --factory --reload
```

FastAPI interactive documentation is then available at `/docs`.

## Validation

The F1 test suite verifies:

- source and evidence creation for manual knowledge;
- stable knowledge identity across edits;
- no duplicate `SourceItem` or `Evidence` on update;
- revision sequence across create, edit and archive;
- logical archive behavior;
- protection against editing imported knowledge as manual knowledge;
- complete HTTP CRUD flow from an initially empty database.

## Important boundary

F1 accepts structured manual knowledge. It does not yet transform unrestricted prose into entities, attributes, relations or procedures with an LLM.

That intelligent-ingestion problem remains separate so it can be evaluated against this deterministic baseline.
