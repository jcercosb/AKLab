# ADR-0004 - Manual knowledge keeps source provenance and revisions

## Status

Accepted in F1.

## Context

F1 introduces knowledge that is created directly inside Applied Knowledge Lab instead of imported from an external database or document.

The source/knowledge/evidence separation established in F0.2 must still hold. A manually entered statement is not allowed to bypass provenance simply because it originated inside the application.

Editing also introduces a new problem: replacing a `KnowledgeItem` in place would silently destroy its previous state.

## Decision

Each knowledge space gets a generic manual source on demand:

```text
manual:<knowledge_space_id>
```

Each manually created knowledge item has a corresponding `SourceItem`:

```text
MANUAL:<uuid>
```

The `SourceItem.raw_content` stores the current manual representation and is linked to the `KnowledgeItem` through evidence of type `manual_entry`.

Manual creation, editing and archival also append a `KnowledgeRevision` containing a JSON snapshot of the knowledge state.

The first revision is revision 1. Subsequent edits increment the revision number.

Imported knowledge cannot be edited through the manual-knowledge service unless it also has explicit manual provenance.

User-facing deletion in F1 is logical deletion:

```text
status = archived
```

Physical deletion is deliberately not exposed.

## Consequences

Manual and imported knowledge share the same canonical knowledge model.

A future UI can edit manual knowledge without needing source-specific logic.

Historical manual states remain inspectable even though `SourceItem.raw_content` represents the current editable source state.

The system can later attach additional evidence to a manually created item without changing its identity.
