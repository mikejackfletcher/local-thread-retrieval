# System Working Model

## Purpose

The System Working Model is a companion layer for understanding this repository as a system.

It gives humans a governed overview of capabilities, modes, components, relationships, seams, boundaries, implications, and extension options. It is designed for walkthrough and comprehension, not for runtime behaviour.

## Core Principle

Understand the system as a system before changing it as code.

Comprehension should precede modification when changes affect capability, topology, seams, or boundaries.

The implementation shows what runs. The System Working Model shows how the running parts fit together, where the seams are, what each capability depends on, and where optionality is preserved or intentionally constrained.

## What This Layer Is For

This layer is for:

- capability maps
- mode descriptions
- structural component overviews
- structural relationship descriptions
- seam and boundary descriptions
- extension-option inventories
- implication notes for future change
- future walkthrough views such as C4-style structural views, capability maps, seam maps, and model/framework views

It should help a reviewer navigate the system without treating implementation files as the only comprehension surface.

## What It Must Help A Human Understand

This layer should help answer:

- What can the system currently do?
- Which capabilities are implemented, inactive, deferred, or speculative?
- Which modules and tables support each capability?
- Where are the main boundaries between source, evidence, retrieval, synthesis, presentation, and action?
- Which seams are intended for extension?
- Which seams are intentionally closed in v1?
- What are the implications of extending or collapsing a seam?
- Which capabilities depend on which structures?

In v1, retrieval semantics are deterministic from source-derived state and query parameters; thread continuity is a sensemaking concern and does not steer retrieval.

## Relationship To Implementation

The System Working Model sits alongside implementation.

It is not a code reference, API reference, or duplicate of module docstrings. It should not restate every function or table. It should describe the system shape at the level needed for reasoning, walkthrough, and safe extension.

When implementation changes alter capabilities, seams, topology, or major relationships, this layer should be updated incrementally.

## Relationship To The Architectural Reasoning Layer

The Architectural Reasoning Layer preserves decision trace, governance posture, invariants, and review discipline.

The System Working Model preserves system comprehension: what exists, how it fits together, what each capability depends on, and where the seams are.

In short:

- Architectural Reasoning Layer: why this design and what must be protected.
- System Working Model: what the system is and how its parts relate.

## Relationship To Spec And Project Brief

- `docs/spec-v1.md` is the constrained engineering contract.
- `docs/project-brief.md` is the north star and cognitive architecture.
- `docs/system-*.md` files are the working model for system understanding, walkthrough, capability reasoning, seam visibility, and architectural comprehension.

The System Working Model must not expand v1 scope. It describes implemented capability, inactive future seams, deferred options, and speculative horizons distinctly.

It is a comprehension layer, not an authority layer.

## What Belongs Here

Include material that improves:

- capability clarity
- seam visibility
- model legibility
- boundary understanding
- implication awareness
- safe future extension

Good entries identify what exists, what it depends on, what boundary it touches, and what future change would need care.

## What Does Not Belong Here

Do not include:

- implementation code
- runtime behaviour not already implemented
- detailed API reference
- duplicate spec text
- speculative design presented as current capability
- hidden automation instructions
- UI or diagram requirements
- broad essays that do not help system understanding

## Final Principle

The System Working Model should make the repository easier to understand without turning understanding into ceremony.

Keep it thin, current, and useful. Separate implemented capability from future possibility, and preserve the system shape clearly enough that future changes can be made deliberately.
