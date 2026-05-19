# Architecture Decision Records

ADRs capture material design decisions that affect this repository's invariants, boundaries, extension seams, topology, governance posture, or hard-to-reverse trade-offs.

They are part of the Architectural Reasoning Layer. Use them to keep significant reasoning inspectable without turning ordinary implementation work into process theatre.

## When To Write One

Write an ADR when a decision:

- changes or defines a system boundary
- protects or weakens an invariant
- creates or changes an extension seam
- affects source truth, evidence, retrieval, synthesis, thread, or backlog semantics
- constrains future implementation choices
- accepts a trade-off that future maintainers may reasonably challenge

Do not write an ADR for small local refactors, mechanical cleanup, or implementation choices with no architectural consequence.

## Minimal ADR Template

```markdown
# ADR: <Title>

## Status

Proposed | Accepted | Superseded

## Context

What situation, constraint, or design pressure requires a decision?

## Decision

What decision was made?

## Constraints / Invariants Protected

Which invariants, boundaries, or governance rules does this protect?

## Alternatives Considered

What other options were considered, and why were they not chosen?

## Consequences

What trade-offs, costs, risks, or future obligations follow from this decision?

## Enforcement

Which tests, schema constraints, validation helpers, or review checks enforce this decision?

## Revisit When

What future condition would justify reopening this decision?
```
