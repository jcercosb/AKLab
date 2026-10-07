ADR-0002 — Knowledge status and confidence do not mean source truth
=======================================================================

Status
------

Accepted in F0.2.

Context
-------

A deterministic import from a source such as SAT.mdb can reproduce the
source faithfully without proving that the source statement is objectively
correct, current, or non-contradictory.

For example, SAT may state that a parameter solves a problem. The import
pipeline can know with certainty where that statement came from while still
not knowing whether the statement remains technically valid.

Decision
--------

KnowledgeItem.status represents lifecycle state, not truth.

Initial lifecycle values may include:

- active
- deprecated
- archived

KnowledgeItem.confidence is reserved for epistemic confidence when such a
score is meaningful.

Deterministically imported source-backed knowledge does not receive an
artificial confidence score, so its initial value is NULL.

Evidence.confidence expresses confidence in the evidence linkage, not in the
objective truth of the source.

A direct SAT mapping initially uses:

KnowledgeItem

    status = active
    confidence = NULL

Evidence

    evidence_type = source_record
    confidence = 1.0

The evidence means "SAT states this", not "this statement is certainly true".

Consequences
------------

Future sources may support, contradict, supersede or qualify an existing
KnowledgeItem without redefining what status means.

Human review, inferred knowledge, contradictions and source authority can be
modelled explicitly later rather than overloading one confidence field.
