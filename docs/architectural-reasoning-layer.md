# Architectural Reasoning Layer

## Purpose

The Architectural Reasoning Layer is a companion governance surface for the build.

Its purpose is to preserve the reasoning, constraints, trade-offs, invariants, dependencies, topology, and challenge surfaces behind the system. It exists so the codebase does not become the only truth surface.

This is not normal documentation. It is an inspectable reasoning layer for implementation decisions that materially affect system boundaries, invariant enforcement, extension seams, governance posture, interpretive behaviour, or irreversible design choices.

The layer should help a human ask:

- Why does this boundary exist?
- What invariant does this decision protect?
- What trade-off was accepted?
- What alternatives were rejected?
- What would break if this changed?
- Which tests hold this decision in place?

## Core Principle

Software is executable reasoning under constraint.

The implementation expresses decisions, but code alone does not always preserve the reasons those decisions were made. Significant design reasoning must remain inspectable and challengeable without requiring a reader to reconstruct intent from code shape alone.

This layer exists to make reasoning visible while resisting uncontrolled reflective overhead.

Capture only reasoning that changes or protects one of the following:

- invariants
- system boundaries
- extension seams
- governance posture
- interpretive behaviour
- irreversible or hard-to-reverse design choices

Do not capture ordinary implementation narration, obvious local choices, or commentary that does not affect future decision quality.

## What This Layer Contains

This layer may contain:

- decision traces for significant design choices
- constraints and invariants that shaped those choices
- challenge questions a reviewer should be able to ask
- test dialogue linking design claims to enforcement
- topology notes explaining how modules and planes relate
- known rejected alternatives and why they were rejected
- future-horizon seams that must remain inactive in v1
- governance posture for boundaries such as source truth, evidence, synthesis, backlog, and external action

This layer must not contain:

- runtime behaviour
- hidden automation instructions
- unimplemented workflow semantics presented as current behaviour
- speculative features without clear future-horizon labelling
- canon promotion rules not yet implemented
- broad design essays that do not constrain the build

## Decision Trace

A decision trace records why a material design choice exists.

Use a decision trace when a choice affects:

- source immutability
- identity and stable IDs
- evidence creation and provenance
- retrieval determinism
- thread boundaries
- synthesis boundaries
- backlog locality
- external integration posture
- rebuildability
- future extension seams

Each decision trace should identify:

- the decision
- the context
- the constraint or invariant being protected
- alternatives considered
- the accepted trade-off
- tests or checks that enforce the decision
- conditions that would justify revisiting it

Decision traces should be concise. They are not post-hoc essays; they are review handles.

## Constraint and Invariant Trace

The system depends on explicit invariants. This layer records how constraints move from doctrine into implementation.

Examples of traceable constraints:

- source files are read-only
- note identity is `(source_root, path)`
- derived stores are rebuildable
- retrieval is deterministic and explainable
- `thread_id` does not alter base retrieval semantics in v1
- evidence excerpts are contiguous source text
- summaries are not evidence
- backlog items are not source truth
- external workflows are not executed in v1

For each material invariant, the trace should make clear:

- where the invariant originates
- where it is represented in code or schema
- which tests enforce it
- what future change would risk violating it

The goal is not to duplicate the spec. The goal is to make enforcement inspectable.

Current v1 retrieval invariant: base retrieval semantics depend only on source-derived records and explicit retrieval query parameters. They do not depend on `thread_id`, thread summaries, pinned evidence, or other sensemaking context. This is represented by `SearchRequest.thread_id` being non-steering input to `search(...)`, and enforced by `test_thread_id_does_not_change_retrieval_set_or_ranking` in `tests/test_retrieval.py`.

## Test Dialogue

Tests are part of the reasoning surface.

The test dialogue records the question each important test is answering. It should connect tests to the design claim they protect.

Examples:

- "Repeated ingestion remains idempotent" tests rebuildability and stable note identity.
- "Generated free text cannot be stored as evidence" tests the boundary between source evidence and generated synthesis.
- "Retrieval remains independent from `thread_id`" tests that thread continuity does not become hidden retrieval steering.
- "Thread ID does not change retrieval set or ranking" tests that varying thread identity in v1 cannot alter retrieved records, ordering, or scores; enforced by `test_thread_id_does_not_change_retrieval_set_or_ranking`.
- "Backlog items are not treated as evidence" tests that action-plane records do not become source truth.

When adding hardening tests, prefer test names and assertions that express the design question directly. Avoid tests that only encode incidental implementation details.

## Design Topology

The Architectural Reasoning Layer should preserve the system topology at the level needed for review.

Current topology:

- Knowledge plane
  - source registration
  - markdown parsing
  - note, metadata, chunk, and link storage
  - deterministic retrieval
  - evidence record creation

- Sensemaking plane
  - threads
  - messages
  - pinned evidence
  - thread summaries
  - context frame assembly

- Action plane
  - internal backlog items
  - backlog evidence links
  - backlog status history

Topology notes should explain boundaries between planes and layers. They should not blur them.

In particular:

- retrieval results are not pinned evidence until explicitly pinned
- evidence is not synthesis
- synthesis is not source
- backlog is not execution
- context frames are presentation surfaces, not external API calls

## Interrogation Surface

Humans should be able to query the architecture.

This layer should support questions such as:

- Which module owns source truth?
- Which records are derived and rebuildable?
- Which functions can create evidence?
- What prevents generated text from becoming evidence?
- What prevents thread summaries from influencing retrieval?
- What prevents backlog items from becoming source truth?
- Which tables are local/internal only?
- Which future seams exist but are intentionally inactive?
- Which tests would fail if a boundary collapsed?

Any future tooling that provides conversational or visual interrogation must treat these questions as first-class queries, not best-effort heuristics.

The doctrine exists now so the design remains queryable by humans, even before tooling exists.

## Interaction Model

The Architectural Reasoning Layer is maintained incrementally by humans and coding agents during build work. It is updated as part of normal change, not in large, infrequent design dumps.

Use it when:

- a design decision changes a boundary
- a new invariant is introduced
- an extension seam is added
- a test begins enforcing a governance claim
- a trade-off constrains future implementation
- a future feature is deliberately deferred

Do not use it for every small function, local refactor, or obvious implementation detail.

The interaction model is:

1. Make the implementation change.
2. Add or update tests that enforce the relevant invariant.
3. Record the reasoning only if it materially affects future review or governance.
4. Keep the reasoning concise enough to remain useful.

## Design Discipline

This layer must resist uncontrolled reflective overhead.

The cost of capturing reasoning is justified only when the reasoning protects future implementation quality. A reasoning record should help a future reviewer avoid collapsing layers, weakening invariants, or misreading a seam as implemented behaviour.

Design discipline rules:

- Prefer precise statements over broad manifestos.
- Link reasoning to constraints, tests, or topology.
- Do not present aspirations as implemented behaviour.
- Do not add autonomous-agent framing.
- Do not create hidden obligations outside the spec.
- Do not use this layer to smuggle in new runtime semantics.
- Keep future-horizon notes clearly labelled as future horizon.

## Relationship to the Broader System

This document has a distinct role from the other project documents:

- `docs/spec-v1.md` is the constrained engineering contract.
- `docs/project-brief.md` is the cognitive architecture and north star.
- `docs/architectural-reasoning-layer.md` is the build-time reasoning, decision trace, and review doctrine.

The Architectural Reasoning Layer sits beside the implementation. It does not override the spec. It does not expand v1 scope. It explains and preserves the reasoning behind boundaries already required by the spec and the project brief.

Its long-term purpose is to keep the system governable as it becomes more capable.

## Final Principle

The codebase must not become the only truth surface.

The system should make its reasoning structure inspectable without turning every implementation detail into ceremony. Preserve the decisions that matter, keep them challengeable, and keep the cognitive layers separate.

Build reasoning into the system without letting reflection become the system.
