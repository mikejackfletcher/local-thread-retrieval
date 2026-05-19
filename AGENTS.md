# Repository Instructions for Coding Agents

This repository includes an Architectural Reasoning Layer. Treat it as a standing repository primitive, not optional documentation.

Before making material changes, read:

- `docs/spec-v1.md`
- `docs/project-brief.md`
- `docs/architectural-reasoning-layer.md`

## Material Change Rule

When a change affects invariants, boundaries, extension seams, governance posture, topology, or hard-to-reverse trade-offs, the agent must:

1. Implement the change.
2. Update or add enforcing tests.
3. Update the relevant reasoning-layer artefact.
4. Reference the reasoning-layer update in its summary.

Relevant reasoning-layer artefacts include ADRs under `docs/adr/`, invariant or topology traces, and any future lightweight reasoning records established by the project.

## Scope Discipline

Do not create reflective overhead for small local refactors, mechanical cleanup, formatting-only changes, or obvious implementation details that do not affect future review or governance.

Do not invent runtime behaviour from doctrine. The Architectural Reasoning Layer explains and governs implementation decisions; it does not expand v1 scope or create unimplemented workflow semantics.

Do not treat the reasoning layer as optional. If a change materially alters a protected boundary or invariant, the reasoning surface must remain current.

## Project Boundaries

Preserve the separation between:

- `docs/spec-v1.md`: constrained engineering contract
- `docs/project-brief.md`: cognitive architecture and north star
- `docs/architectural-reasoning-layer.md`: build-time reasoning, decision trace, and review doctrine

The implementation must remain local-first, provenance-preserving, deterministic where specified, and explicit about state changes. Do not add autonomous-agent framing, hidden behaviour, external workflow execution, or source mutation.
