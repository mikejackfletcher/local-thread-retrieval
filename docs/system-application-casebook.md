# System Application Casebook

## Purpose

This casebook records recurring ways the System Working Model is applied.

It is intended as a reusable pattern for this repo and future Codex work. Each pattern describes a scenario, what the System Working Model makes visible, and the intended outcome.

## Archetypal Patterns

### Understanding A Newly Generated Codebase

Scenario:

A reviewer inherits a codebase produced through rapid implementation and needs to understand what it actually does before changing it.

What the System Working Model makes visible:

- implemented capabilities
- major modules and data structures
- source-of-truth boundaries
- active versus inactive seams
- tests that protect the current shape

Intended outcome:

The reviewer can explain the system in capability and boundary terms before editing code.

### Reviewing Architectural Drift After Rapid AI-Assisted Changes

Scenario:

Several features have been added quickly, and the team needs to check whether boundaries have collapsed or scope has drifted.

What the System Working Model makes visible:

- new capabilities added since the last review
- seams that moved or became ambiguous
- implied behaviour not backed by tests
- places where derived artefacts could be mistaken for source truth
- gaps between implementation and doctrine

Intended outcome:

The team can identify drift early and decide whether to harden, revert, document, or defer.

### Exposing Hidden Seams And Future Options

Scenario:

The system appears simple, but future extension depends on knowing where safe attachment points already exist.

What the System Working Model makes visible:

- extension seams
- inactive future seams
- deferred options
- boundaries that must remain closed in v1
- structures that enable future work without implementing it now

Intended outcome:

Future work can attach deliberately without smuggling in runtime behaviour or collapsing current invariants.

### Walking A Stakeholder Through What The System Actually Does

Scenario:

A stakeholder needs a plain explanation of the system without reading source files or implementation details.

What the System Working Model makes visible:

- capabilities in operational language
- data flow at a system level
- what is local and internal
- what is explicitly out of scope
- how provenance is preserved
- where human judgement remains authoritative

Intended outcome:

The stakeholder understands the system's current behaviour, limits, and extension posture without mistaking future intent for implemented capability.

### Distinguishing Implemented Capability From Speculative Design

Scenario:

Planning discussions begin to blur what exists, what is deferred, and what is only a horizon.

What the System Working Model makes visible:

- implemented capability
- inactive future seam
- deferred option
- speculative horizon
- tests or structures that prove current behaviour

Intended outcome:

The team can plan without accidentally treating speculative design as current system behaviour.

### Preparing For Refactor Or Extension Work Safely

Scenario:

A module needs to be refactored or extended, and the risk is not local syntax but system-boundary damage.

What the System Working Model makes visible:

- capabilities depending on the module
- invariants the module helps enforce
- seams that must remain stable
- tests that should fail if the refactor breaks a boundary
- implications for future extension

Intended outcome:

The refactor proceeds with a clear picture of system dependencies and protected boundaries.

## What Each Pattern Helps Reveal

Across patterns, the System Working Model should reveal:

- capability shape
- boundary health
- seam status
- dependency structure
- implemented versus future state
- risks of architectural drift
- safe extension paths

## Status

This casebook is a living companion to the System Working Model. Add patterns only when they recur often enough to guide future review or implementation work.
