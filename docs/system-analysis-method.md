# System Analysis Method

## Purpose

This document defines a reusable analysis lens for interrogating the implemented system.

It describes how to look at the system so a reviewer can understand capability, structure, boundaries, assumptions, seams, and implications without confusing implemented behaviour with intended or speculative behaviour.

## Orientation

Begin with the basic system question:

What is this system actually for?

Then establish:

- current purpose
- implemented capabilities
- non-goals
- source-of-truth boundaries
- major planes and layers
- visible state transitions
- local/internal records versus source material

Do not begin by cataloguing files. Begin by identifying system function.

## Diagnose

Diagnose the system by asking:

- What capabilities are real and tested?
- What is implied but not implemented?
- Where could a reader mistake a derived artefact for source truth?
- Where could thread context become hidden retrieval steering?
- Where could backlog records become action execution?
- Which dependencies are structural, and which are incidental?
- Which assumptions are carried by tests rather than by prose?

Diagnosis should reveal risk surfaces, not produce broad critique.

## Simplify

Simplify by naming the few structures that explain the most behaviour.

For this repo, the main simplifying distinctions are:

- source notes versus derived stores
- evidence versus synthesis
- retrieval results versus pinned evidence
- thread continuity versus retrieval semantics
- backlog tracking versus external execution
- presentation frames versus external API calls

Use these distinctions before introducing finer detail.

## Structure

Describe structure in layers:

- source material
- parsed notes and chunks
- retrieval
- evidence records
- threads and summaries
- context frame assembly
- backlog records
- invariant and validation helpers

For each layer, ask:

- What owns the data?
- What creates it?
- What can modify it?
- What must it never be treated as?
- Which tests enforce the boundary?

## Capability And Seam Analysis

For each capability, identify:

- current implemented behaviour
- backing tables or modules
- inputs and outputs
- constraints
- seams for future extension
- inactive future seams
- deferred options

Useful review questions:

- Which capabilities depend on which structures?
- Which parts are fixed by invariant?
- Which parts are designed for extension?
- Which seam would be dangerous to collapse?
- Where is optionality preserved?
- Where is optionality intentionally constrained?

## Implications And Trade-offs

For each material design shape, ask:

- What does this make easier?
- What does this make harder?
- What future feature does this enable?
- What future shortcut does this prevent?
- What invariant does this protect?
- What would break if this changed?

Trade-offs should be tied to system behaviour, not personal preference.

## Review Questions

Use these questions during review:

- What is this system actually for?
- What are its major capabilities?
- What is implemented versus implied?
- What are the main boundaries and seams?
- Which parts are fixed versus designed for extension?
- What assumptions is the system carrying?
- What would break if a seam collapsed?
- Which capabilities depend on which structures?
- Where is optionality preserved versus intentionally constrained?
- Which tests would catch a boundary violation?

## Signature Traits

A good system analysis in this repo is:

- precise
- implementation-aware
- boundary-sensitive
- concise
- explicit about implemented versus future capability
- resistant to hype
- free of autonomous-agent framing
- useful for safe extension
