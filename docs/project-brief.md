# Codex Project Brief: Local-First Thread-Aware Retrieval System

## 1. North Star: What We Are Ultimately Building

We are not building a generic knowledge base or a generic AI assistant.

We are building a composable cognitive substrate: a local-first, provenance-preserving sensemaking system for long-running human-AI knowledge work.

Core properties of the eventual system:

- Material remains reusable: the same source evidence can support many threads and outputs.
- Interpretation remains separable: interpretations sit on top of evidence; they never overwrite it.
- Perspectives remain swappable: different lenses and frames can be applied without losing history.
- Synthesis remains reconstructable: any synthesis can be traced back to the exact evidence, query, and lens that produced it.
- No single lens becomes canon accidentally: nothing becomes "truth" just because it was once surfaced as an answer.

Underlying principle:

> The system must preserve optionality of interpretation.
> Evidence is stable; interpretations are plural, revisitable, and never silently promoted to canon.

## 2. Material Ontology: What Kinds of Things Exist

The system distinguishes three material classes:

1. Source evidence
   - Read-only, provenance-preserving source materials such as markdown notes and transcripts.
   - This is the only "ground truth" the system can rely on.

2. Derived artefacts
   - Retrieval results, evidence slices, summaries, syntheses, thread structures, and working notes.
   - Always linked back to explicit source evidence; never treated as canon.

3. Operator-approved canon
   - Explicitly promoted, human-governed durable knowledge.
   - Promotion into canon always requires an explicit human action.

Rules:

- Derived artefacts are not canon.
- Threads are not canon.
- Summaries are not evidence.
- Backlog items are not source truth.
- Canon promotion is explicit and human-driven.

## 3. Layered Cognitive Pipeline: What Must Stay Separate

We are explicitly protecting against premature cognitive collapse, where systems silently compress everything into one opaque answer.

Keep the following layers structurally distinct:

1. Source material
   - The original documents, notes, and transcripts. Never mutated.

2. Raw evidence
   - Concrete slices or spans of source material selected as relevant for a context.

3. Retrieval
   - The deterministic process and result of choosing "this is the evidence set for this query or thread."

4. Lens / frame
   - The viewpoint or question applied to evidence, such as a risk lens, architecture lens, or user-journey lens.

5. Synthesis
   - Constructed meaning: summaries, narratives, hypotheses, and similar material.
   - Always tagged with evidence set, lens, time, and thread.

6. Presentation
   - How synthesis is rendered: structure, ordering, formatting, and UX.
   - Swappable without changing synthesis or evidence.

7. Action
   - Backlog items, proposed steps, and decisions.
   - Explicitly linked back to synthesis, lens, and evidence.

Design rule:

> Do not collapse these layers.
> Each layer must have its own data structure, identity, and audit trail.

## 4. Planes and Decision Rights

The system is structured into three planes:

- Knowledge plane: ingestion, parsing, retrieval structures, provenance-preserving storage.
- Sensemaking plane: threads, evidence pinning, synthesis, contextual continuity.
- Action plane: internal backlog shaping and explicit, human-reviewed action tracking.

Decision rights:

- The system may retrieve, rank, group, summarize, and propose.
- The system may not mutate source, merge threads implicitly, create evidence-free actions, execute external workflows, redefine canon, or hide state transitions.
- Human judgement remains authoritative over evidence selection, backlog confirmation, canon promotion, interpretation of synthesis, and externalisation of action.

## 5. v1 Scope: What This Iteration Builds

This iteration is not trying to build the full cognitive substrate.

v1 goal:

A local-first, read-only retrieval and sensemaking instrument that can:

1. Read markdown notes and transcripts from a local Obsidian/iCloud vault, read-only.
2. Build deterministic, provenance-linked retrieval structures over those materials.
3. Let the operator run governed queries, inspect and select evidence slices, and pin evidence into threads.
4. Generate clearly labelled synthesis that is explicitly tied to specific evidence and a lens, and is never treated as source or canon.
5. Assemble grounded context packages for LLM-assisted analysis, where all included evidence and synthesis remains inspectable and traceable.

In other words: v1 is a governed evidence and synthesis loop, not a full operating system.

## 6. v1 Constraints: Hard Behavioral Rules

For this implementation phase:

- Source materials are strictly read-only.
- No silent note mutation.
- No autonomous external actions.
- No hidden behaviour.
- No external workflow execution.
- All state changes are explicit and inspectable.
- Provenance is preserved end-to-end.
- Local-first behaviour: state is primarily local, with any sync, if added later, treated carefully.

Retrieval philosophy in v1:

- Retrieval is governed deterministic retrieval, not opaque latent semantic inference.
- The retrieval layer must remain deterministic, explainable, provenance-preserving, user-inspectable, and operationally constrained.

Thread-awareness in v1:

- Threads support continuity, grouping, and inspection of retrieved evidence only.
- Thread context must not silently alter retrieval ranking, query semantics, or retrieval scope.
- Threads in v1 are organizational and contextual; they are not a hidden prior over retrieval.

## 7. Invariants / Fitness Functions: What Must Always Hold

Every code change must respect these invariants:

1. Determinism
   - Given the same sources and configuration, retrieval results must be repeatable.
   - Re-ingesting unchanged materials must be idempotent.

2. Provenance
   - Every derived artefact must carry links to source identifiers, source spans or locations, retrieval query and parameters, and timestamp and actor where applicable.

3. Rebuildability
   - Any derived structure must be reconstructable from source evidence, stored metadata, and a known set of rules.

4. Interpretive optionality
   - No interpretation or synthesis is ever treated as canon by default.
   - Multiple interpretations can coexist for the same evidence set.

5. Explicit state
   - No hidden caches or opaque state transitions.
   - Any create, update, or delete of derived artefacts is visible and explainable.

6. Human authority
   - The system must not auto-promote anything into canon.
   - Any canon promotion or external action must be human-initiated and clearly recorded.

## 8. Non-Goals for v1: What Not to Build Yet

Do not implement in v1:

- Canon promotion workflows or governance kernels.
- Automated backlog execution or external workflow runners.
- Cross-thread synthesis or global summarization.
- Thread context influencing base retrieval semantics.
- Multi-user collaboration, sync, or distributed conflict resolution.
- Any hidden or implicit memory/learning behaviour.

Extension points may exist, but they must remain unimplemented or stubbed with clear future-horizon labels.

## 9. Identity and Event Discipline

Even in v1, adopt a lightweight identity and mutation model:

- Assign stable IDs for sources, evidence segments, threads, syntheses, and backlog items.
- Represent state changes as small, explicit events where applicable, including actor, timestamp, operation, target IDs, and evidence references for any synthesis or backlog.

v1 does not need a full event-sourcing engine, but data structures should allow a more formal event log later without breaking the model.

## 10. Design Rule for Every Increment

For every module or feature:

- It must be useful on its own for the v1 evidence-and-synthesis loop.
- It must keep source, evidence, retrieval, lens, synthesis, presentation, and action separable.
- It must remain compatible with the north star: no shortcuts that embed interpretation into source or collapse layers into an opaque blob.

In short:

> Build for today, align to tomorrow, preserve the separations.
