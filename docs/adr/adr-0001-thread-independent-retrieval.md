# ADR: Thread-Independent Retrieval In v1

## Status

Accepted

## Context

Thread context supports sensemaking continuity in v1, but it must not silently steer base retrieval. If `thread_id`, thread summaries, or pinned evidence influenced retrieval semantics, the same source materials and query could produce different results without an explicit retrieval parameter change.

## Decision

v1 retrieval semantics remain independent from thread identity and thread context. Base retrieval results are a function of source-derived records and explicit retrieval query parameters only.

## Constraints / Invariants Protected

- determinism of repeated retrieval
- explainable keyword scoring and sorting
- rebuildability from source-derived state and stored metadata
- separation between retrieval and sensemaking planes
- governance rule that thread continuity does not become hidden retrieval steering

## Alternatives Considered

- Allow `thread_id` to bias or filter retrieval results. Rejected for v1 because it would introduce hidden ranking behaviour and blur retrieval with sensemaking context.
- Use thread summaries or pinned evidence as query expansion. Rejected for v1 because summaries are not evidence and thread state is not source truth.

## Consequences

Thread-aware retrieval remains a future option rather than a current behaviour. Any future use of thread context in retrieval must be explicit, governed, and separately tested.

## Enforcement

Enforced by `test_thread_id_does_not_change_retrieval_set_or_ranking` in `tests/test_retrieval.py` and the v1 retrieval invariant trace in `docs/architectural-reasoning-layer.md`.

## Revisit When

Revisit when considering v2 governed thread-aware retrieval features with explicit query semantics, visible parameters, and provenance-preserving explanation.
