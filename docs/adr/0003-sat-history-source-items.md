ADR-0003 — SAT HISTORICO is source history, not automatic knowledge
=====================================================================

Status
------

Accepted in F0.2.

Context
-------

The real SAT.mdb contains 10,369 HISTORICO rows. Every row has a unique
ID_HISTORICO. Of those rows, 10,188 reference an existing CONSULTAS row through
ID_BOLETIN and 181 reference a consultation that is no longer present in the
current CONSULTAS table.

The content is heterogeneous. It includes technical follow-up, version notes,
procedural information and operational events such as changes of responsible
technician. Therefore one HISTORICO row cannot safely be treated as one unit of
confirmed technical knowledge.

Decision
--------

Each HISTORICO row is imported as its own SourceItem.

Its stable external identifier is:

    HISTORICO:<ID_HISTORICO>

When ID_BOLETIN is present, the source relationship is preserved generically as:

    parent_external_id = CONSULTAS:<ID_BOLETIN>

The parent is not a database foreign key because source data may legitimately
contain orphan references. Orphan HISTORICO rows are preserved rather than
removed, repaired or attached to an invented consultation.

The deterministic F0 normalizer creates KnowledgeItem objects only for
CONSULTAS rows. HISTORICO remains source evidence until a later extraction or
classification stage determines whether a specific historical entry contains
reusable technical knowledge.

Consequences
------------

Source fidelity is maintained for all historical rows, including orphans.

The generic core gains a source-level parent_external_id concept without
learning anything about SAT-specific ID_BOLETIN semantics.

Future AI experiments can classify HISTORICO entries and propose technical
KnowledgeCandidate objects without changing the source representation.
