# Current State

## What Currently Exists

- Local SQLite schema for sources, notes, chunks, links, evidence, threads, pinned evidence, summaries, backlog items, and backlog history.
- Manual markdown source registration and rescanning.
- Markdown parsing for front matter, headings, links, and deterministic chunk creation.
- File hash tracking with deterministic replacement of derived records on changed files.
- Removal of derived records when source files are removed.
- Keyword retrieval over note titles, tags, front matter, and chunk text.
- Deterministic retrieval ranking, latest sorting, provenance fields, and explainable scoring.
- Evidence creation from existing chunks with bounded contiguous excerpts.
- Thread creation, thread messages, evidence pinning, and stored thread summaries.
- Local/internal backlog items linked to existing evidence with constrained status transitions.
- ChatGPT context frame assembly for manual copy/paste, including retrieval results, evidence, thread context, and provenance.
- Hardening tests and validation helpers for rebuildability, provenance, idempotence, source immutability, and plane separation.
- Doctrine and governance docs for project scope, architectural reasoning, ADRs, and system working-model practices.

## What Is Stable

- Source markdown remains read-only.
- Ingestion is idempotent for unchanged files.
- Note identity is based on source root and path.
- Derived note records, chunks, metadata, and links are rebuildable from source files.
- Retrieval is deterministic and explainable.
- `thread_id` does not alter base retrieval semantics in v1.
- Evidence can only be created from existing chunks.
- Evidence excerpts remain contiguous source text and are capped at 500 characters.
- Thread summaries are stored as summaries, not evidence.
- Backlog items require evidence and are not treated as source truth.
- External workflow execution is absent.

## What Is Intentionally Missing

- UI.
- Embeddings or semantic retrieval.
- Autonomous retrieval or autonomous actions.
- Source markdown mutation or write-back.
- External integrations.
- Canon promotion workflows.
- Thread-aware retrieval steering.
- Cross-thread synthesis.
- Workflow execution from backlog items.
- File watching or background automation.

## Biggest Current Risks

- The system is library/test driven; operational entry points are still minimal.
- Schema and behaviour are covered by tests, but there is no migration/versioning discipline yet.
- Context frame assembly is manual copy/paste only, so output review remains human-operated.
- Future retrieval extensions could accidentally blur retrieval, thread state, and synthesis unless guarded by tests and ADRs.
- Documentation layers are now useful but could become stale if future material changes do not update them.

## Likely Next Strategic Directions

- Add a small command-line interface for explicit local operations such as register, rescan, search, create evidence, and assemble frame.
- Define database migration/versioning conventions before schema changes accumulate.
- Expand deterministic retrieval controls without introducing hidden ranking behaviour.
- Add governed synthesis records only if tied explicitly to evidence, lens, thread, and provenance.
- Build a minimal inspection surface for sources, chunks, evidence, threads, and backlog state.
- Keep semantic retrieval, external integrations, source write-back, and canon workflows deferred until separately specified.
