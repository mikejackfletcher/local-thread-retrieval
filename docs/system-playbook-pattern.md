# System Playbook Pattern

## Purpose

This playbook describes how to build and maintain the System Working Model alongside implementation.

Its purpose is to keep system understanding current without creating process theatre.

## Orientation

Use the System Working Model when a change affects how the system is understood:

- a new capability appears
- a capability changes responsibility
- a seam opens, closes, or moves
- a boundary becomes more important
- a future option becomes clearer
- an implication affects safe extension

Do not update it for every small local refactor.

## Iteration Pattern

Each update should be thin and useful.

Preferred pattern:

1. Make or review the implementation change.
2. Identify whether the system shape changed.
3. Update the smallest relevant system-model section.
4. Distinguish implemented capability from inactive future seam, deferred option, or speculative horizon.
5. Keep the update tied to walkthrough, capability reasoning, seam visibility, boundary understanding, or implication awareness.

## Capability Capture

When capturing a capability, record:

- what the capability does
- whether it is implemented
- which structures support it
- what input it expects
- what output it creates
- which boundary it touches
- what it must not be mistaken for

Avoid function-by-function narration. Capture the capability as a system behaviour.

## Seam Capture

When capturing a seam, record:

- what the seam separates
- why the seam exists
- whether it is active, inactive, deferred, or speculative
- what could safely attach there later
- what would violate the current scope
- which invariant would be at risk if the seam collapsed

Name seams plainly. A seam is useful only if a future reviewer can recognize it in the implementation.

## Implication Capture

Capture implications when they affect future work.

Useful implication types:

- extension implication
- boundary implication
- testing implication
- data-model implication
- rebuildability implication
- governance implication

Do not capture vague possibilities. Capture implications that materially change how the system should be maintained or extended.

## Review Rhythm

Review this layer when:

- adding a new module with system-level responsibility
- changing retrieval, evidence, thread, synthesis, frame, or backlog semantics
- adding a future seam
- hardening an invariant
- preparing for refactor or extension work
- reviewing rapid AI-assisted changes for architectural drift

The review question is: does the current working model still help a human understand the system as it exists?

## Expansion Discipline

The System Working Model should expand slowly.

Prefer:

- thin updates
- practical descriptions
- current capability over speculation
- clearly labelled future seams
- explicit implemented/deferred distinctions

Avoid:

- large reflective dumps
- broad manifestos
- duplicate spec language
- diagrams without maintained meaning
- speculative horizons described as if implemented

Each update should improve one or more of:

- capability clarity
- seam visibility
- model legibility
- boundary understanding
- implication awareness

## Signature Traits

A healthy playbook update is:

- incremental
- concise
- tied to implemented shape
- explicit about future status
- useful for walkthrough
- useful for review
- safe for future Codex work
