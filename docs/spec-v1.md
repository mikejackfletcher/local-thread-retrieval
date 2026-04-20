Revised Constrained v1 Build Spec: Local-First Thread-Aware Retrieval System
Purpose
This document defines a constrained v1 build spec for a local-first, thread-aware retrieval system over an Obsidian vault and selected iCloud folders. The goal is to define the first working system precisely enough that schemas, boundaries, retrieval behavior, persistence rules, human-control points, and non-goals are not invented during implementation.

The system is not a general autonomous agent. It is a local knowledge system that reads markdown sources, builds retrieval structures, supports thread-based sensemaking, and stores internal Jira-shaped backlog items for later human action rather than triggering external workflows in v1.

What this system is not
This system is not:

an autonomous agent;

a workflow execution engine;

a system that mutates source notes in v1;

a replacement for the Obsidian vault or the underlying markdown corpus;

a knowledge graph that infers truth beyond linked evidence.

v1 product statement
The v1 system is a desktop-local service and interface that:

reads an Obsidian vault and selected iCloud folders as markdown sources;

parses front matter, headings, links, timestamps, and file metadata;

builds local retrieval indexes and materialized search structures;

allows users to create and continue threads;

allows threads to pin source evidence explicitly;

generates internal backlog items shaped like Jira tickets, but stored locally;

never writes silently back to source notes;

never executes external workflows in v1.

Core invariants
The following rules are system invariants and must be enforced in code, not left to prompts or UI conventions.

Source of truth
Markdown files in the Obsidian vault and approved iCloud folders are the source of truth for notes.

Local indexes, chunks, embeddings, caches, and metadata tables are materialized views derived from source files and may be rebuilt from source at any time.

Thread state is not a source note and must never be treated as equivalent to a note.

Internal backlog items are not source notes and must never be written into the vault unless a future explicit export/write-back feature is added.

Human control
The system may retrieve, rank, group, summarize, and propose.

The system may persist thread state and internal backlog items.

The system may not silently mutate source notes.

The system may not merge threads without explicit user action.

The system may not create a backlog item without linked source evidence.

The system may not execute external API actions in v1.

Visible state changes
Any action that changes system state, including pinning evidence, creating backlog items, changing backlog status, updating thread summaries, rescanning sources, or rebuilding derived stores, must be user-initiated and visible in the UI.

No implicit or automatic state mutation is allowed in v1.

Provenance
Every displayed evidence excerpt must retain source provenance: note ID, file path, heading or section context, and timestamp metadata.

Every backlog item must link to one or more source evidence records.

No synthesis may be presented as sourced evidence unless linked to explicit evidence records.

Evidence excerpts must be contiguous source text from a note or chunk.

Evidence excerpts must not be model-generated, paraphrased, or stitched from multiple non-contiguous fragments.

Evidence excerpts may use ellipsis only at excerpt boundaries.

Evidence excerpts must respect a defined maximum length of 500 characters.

Rebuild invariants
Ingestion must be idempotent.

Note identity is the pair (source_root, path).

Repeated scans of unchanged files must not create duplicate notes, chunks, evidence records, or links.

Updated files must replace derived records based on note identity and file hash.

Deleted files must remove corresponding derived records on rescan.

Rebuilding derived stores must not alter source notes.

System boundaries and decision rights
The spec must clearly separate what the system can know, infer, persist, propose, and enact.

Domain	v1 rule
Source notes	Read-only, source of truth.
Local derived stores	Allowed; rebuildable from source.
Retrieval judgments	Allowed as ranked suggestions, not ground truth.
Synthesis in threads	Allowed when linked to explicit evidence.
Internal backlog shaping	Allowed with evidence links and status.
Source note mutation	Not allowed in v1.
External workflow execution	Not allowed in v1.
Thread merge/split	Manual only.
Decision rights are as follows:

The system decides ranking, chunk retrieval, and deterministic relatedness suggestions.

The system may generate draft summaries and draft backlog items.

The user decides what evidence is pinned into a thread.

The user decides whether a proposed backlog item should exist, be edited, be triaged, or be dropped.

The system does not decide to write to external systems in v1.

Three-plane architecture
The implementation must separate three planes so a coding agent does not collapse them into one fuzzy application boundary.

Knowledge plane
The knowledge plane handles note ingestion and retrieval structures.

Responsibilities:

filesystem watching or periodic scanning;

markdown parsing;

front matter extraction;

heading and section segmentation;

wikilink and relation extraction;

chunk creation;

keyword index creation;

optional vector embedding creation;

provenance-preserving note and chunk storage.

Persistent structures:

notes table;

note metadata table;

chunks table;

links table;

index metadata;

embedding store or embedding columns.

Sensemaking plane
The sensemaking plane handles thread creation, retrieval use inside threads, evidence pinning, and synthesis.

Responsibilities:

create thread;

continue thread;

run search in thread context;

pin evidence;

store thread summaries and open questions;

track what source evidence informed a thread.

Persistent structures:

threads table;

thread messages table;

pinned evidence table;

thread synthesis table.

Action plane
The action plane handles internal backlog shaping only.

Responsibilities:

create internal Jira-shaped backlog item drafts;

attach source evidence references;

manage status transitions such as proposed, triaged, ready, done, dropped;

log user decisions about proposed work.

Persistent structures:

backlog items table;

backlog evidence link table;

backlog history table.

Functional scope for v1
In scope
Register one or more local source folders.

Scan and parse markdown notes.

Extract front matter and filesystem metadata.

Build keyword retrieval.

Support optional hybrid retrieval if embeddings are configured.

Return ranked note and chunk results with provenance.

Create threads.

Add retrieved evidence to threads.

Store thread-level synthesis with source references.

Create internal Jira-style backlog items from pinned evidence.

Search and filter backlog items by status, priority, tag, thread, and source note.

Out of scope
External Jira integration.

Silent write-back to markdown.

Automatic note editing.

Autonomous workflow execution.

Multi-user collaboration.

Cross-device sync orchestration beyond what iCloud and Obsidian already provide.

Full policy engine for external actions.

Email, calendar, or third-party SaaS actions.

Data model
Note record
json
{
  "note_id": "uuid",
  "path": "string",
  "source_root": "string",
  "title": "string",
  "front_matter": {},
  "tags": ["string"],
  "wikilinks": ["string"],
  "created_at": "datetime|null",
  "updated_at": "datetime|null",
  "file_mtime": "datetime",
  "file_hash": "string",
  "parse_status": "ok|error"
}
Chunk record
json
{
  "chunk_id": "uuid",
  "note_id": "uuid",
  "section_path": ["string"],
  "heading": "string|null",
  "text": "string",
  "char_start": 0,
  "char_end": 0,
  "chunk_index": 0,
  "retrieval_text": "string",
  "embedding_vector": null
}
Evidence record
json
{
  "evidence_id": "uuid",
  "note_id": "uuid",
  "chunk_id": "uuid|null",
  "path": "string",
  "title": "string",
  "section_path": ["string"],
  "excerpt": "string",
  "updated_at": "datetime|null",
  "retrieval_score": 0.0,
  "retrieval_mode": "keyword|hybrid|semantic"
}
Thread record
json
{
  "thread_id": "uuid",
  "title": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "status": "active|paused|archived",
  "summary": "string|null"
}
Thread message record
json
{
  "message_id": "uuid",
  "thread_id": "uuid",
  "role": "user|system|assistant",
  "content": "string",
  "created_at": "datetime"
}
Pinned evidence record
json
{
  "pin_id": "uuid",
  "thread_id": "uuid",
  "evidence_id": "uuid",
  "pinned_at": "datetime",
  "pin_reason": "string|null"
}
Thread summary rules
Thread summaries may reference evidence IDs but must not be stored as evidence records.

Thread summaries must not embed source text as if it were evidence.

Thread summaries must not be used as retrieval input.

Thread summaries must never be treated as source notes.

Backlog item record
json
{
  "backlog_id": "uuid",
  "thread_id": "uuid|null",
  "title": "string",
  "description": "string",
  "status": "proposed|triaged|ready|done|dropped",
  "priority": "low|medium|high",
  "action_type": "review|write-note|follow-up|research|externalise",
  "confidence": 0.0,
  "requires_confirmation": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
Confidence semantics
confidence represents the system estimate of how well the linked evidence supports the backlog item.

confidence does not represent probability of correctness.

confidence must be derived only from available evidence and retrieval signals, not from unsupported model assertions.

Backlog evidence link record
json
{
  "link_id": "uuid",
  "backlog_id": "uuid",
  "evidence_id": "uuid",
  "link_type": "supporting|primary"
}
Retrieval behavior
The spec must define retrieval clearly so implementation does not invent semantics at runtime.

Retrieval modes
v1 minimum: keyword retrieval over title, front matter, tags, headings, and chunk text.

v1 optional: hybrid retrieval combining lexical search with embeddings.

Semantic-only retrieval is not sufficient on its own for v1 because exact titles, tags, acronyms, and front matter values are important in note systems.

Query handling
All retrieval requests accept:

json
{
  "query_text": "string",
  "thread_id": "uuid|null",
  "filters": {
    "tags_any": ["string"],
    "status_any": ["string"],
    "source_roots": ["string"],
    "paths_prefix": ["string"]
  },
  "sort_mode": "relevance|latest",
  "limit": 10
}
Thread influence on retrieval
In v1, thread_id may be used for logging, UI continuity, and future-safe interface consistency.

In v1, thread_id must not silently alter retrieval ranking, filters, scope, or base query semantics.

Query expansion based on thread context is out of scope for v1 unless made explicit, separately labeled, and user-visible.

Definition of latest
The term latest must never be inferred loosely.

Default v1 rule:

Filter matching notes and chunks by query and explicit filters.

Rank by lexical or hybrid relevance.

For sort_mode = latest, sort ties first by front matter updated if present, then by filesystem modification time, then by path for deterministic ordering.

Return the tie-break fields in the response.

Related notes behavior
GET /notes/{note_id}/related must use deterministic relatedness rules.

v1 relatedness is computed from:

shared wikilinks, including bidirectional links if present;

shared tags;

optional embedding similarity if hybrid retrieval is enabled.

The related-notes response must include, for each result:

related_note_id

path

title

relation_types, one or more of shared_wikilink, backlink, shared_tag, embedding_similarity

relation_score

Retrieval response
json
{
  "query_id": "uuid",
  "results": [
    {
      "evidence_id": "uuid",
      "note_id": "uuid",
      "chunk_id": "uuid|null",
      "title": "string",
      "path": "string",
      "section_path": ["string"],
      "excerpt": "string",
      "retrieval_score": 0.0,
      "updated_at": "datetime|null",
      "file_mtime": "datetime",
      "provenance": {
        "source_root": "string",
        "heading": "string|null"
      }
    }
  ]
}
Thread behavior
Threads are explicit working contexts, not hidden memory stores.

Thread rules
A thread may reference many notes.

A note may appear in many threads.

A thread stores conversation history, pinned evidence, summaries, and open questions.

Thread summaries are derived and editable, not source truth.

No thread may silently absorb content from another thread.

Merge or split operations are out of scope for v1 unless done manually in the UI.

Evidence pinning
Search results are transient retrieval outputs.

Evidence becomes part of working thread context only when explicitly pinned.

Any thread synthesis shown as evidence-based must enumerate pinned evidence IDs.

Internal backlog behavior
The backlog replaces external Jira execution in v1. It is Jira-shaped for familiarity and future extensibility, but remains local and internal.

Backlog rules
A backlog item must be created from one or more evidence records.

A backlog item may optionally attach to a thread.

A backlog item status must begin as proposed.

Transition to triaged, ready, done, or dropped requires explicit user action.

The system may draft a backlog title, description, priority, action type, and confidence, but the user remains the final decision maker.

No backlog item may trigger external side effects in v1.

Suggested backlog creation workflow
User retrieves notes or works inside a thread.

User pins relevant evidence.

System offers “Create backlog item from pinned evidence.”

System drafts title, description, priority, action type, and confidence.

User edits, confirms, or cancels.

If confirmed, backlog item is stored locally with linked evidence.

API surface
The build must expose stable internal APIs or service boundaries even if the first UI is local-only.

Source registration
POST /sources/register

GET /sources

POST /sources/rescan

Retrieval
POST /search

GET /notes/{note_id}

GET /notes/{note_id}/related

GET /evidence/{evidence_id}

Threads
POST /threads

GET /threads

GET /threads/{thread_id}

POST /threads/{thread_id}/messages

POST /threads/{thread_id}/pins

DELETE /threads/{thread_id}/pins/{pin_id}

POST /threads/{thread_id}/summaries

Backlog
POST /backlog

GET /backlog

GET /backlog/{backlog_id}

PATCH /backlog/{backlog_id}

POST /backlog/{backlog_id}/links

GET /backlog?status=proposed

Storage and local-first requirements
The application must run with local storage as the default mode.

All derived data must be stored in a local database such as SQLite or DuckDB.

Source files are accessed through local filesystem paths.

The system must tolerate iCloud-backed folders appearing as normal filesystem directories on macOS, while handling missing or unavailable files gracefully.

Deleting derived stores must not delete source notes.

Rebuilding indexes must be a supported maintenance path.

UX requirements
The first interface can be minimal, but it must make the boundaries visible.

Required screens or views
Source configuration.

Search and results view.

Note detail view with provenance.

Thread list and thread detail view.

Pinned evidence panel.

Backlog list and backlog detail view.

UX invariants
Search results must show source path and title.

Pinned evidence must remain inspectable from the thread.

Backlog items must display linked evidence.

No UI control may imply that the system has written back to notes when it has not.

Any generated summary or draft must be visually distinguishable from source text.

Any state-changing action must be user-initiated and visible.

Failure modes and non-goals
These must be treated as explicit non-goals and test cases.

Non-goals
No silent mutation of source notes.

No evidence attachment without provenance.

No backlog item creation without linked evidence.

No latest-note resolution without deterministic tie-break rules.

No autonomous execution of external workflows in v1.

No implicit merge of threads.

No treating thread summaries as note content.

No hidden retrieval steering from thread context.

Failure modes to guard against
Parser failure on malformed front matter.

Duplicate notes from overlapping source roots.

Retrieval returning stale notes when latest is requested.

Evidence excerpts detached from true section context.

Model-generated excerpts being mistaken for evidence.

Backlog items generated from unpinned or ambiguous evidence.

Derived stores drifting from source after file changes.

UI ambiguity between source notes and generated summaries.

Hidden state changes triggered by interface side effects.

Acceptance criteria
The implementation is acceptable for v1 only if all of the following are true:

A local source folder can be registered and scanned successfully.

Markdown files with front matter are parsed into note records.

Search returns ranked results with provenance fields.

thread_id does not alter retrieval ranking or scope in v1.

GET /notes/{note_id}/related returns relation types with deterministic relatedness rules.

Evidence excerpts are contiguous source text and never model-generated.

A user can create a thread and pin evidence into it.

A thread summary can reference pinned evidence without altering source notes and without being reused as retrieval input.

A backlog item can be created only from linked evidence.

A backlog item remains local and does not call external systems.

Rebuilding derived indexes leaves source notes unchanged and does not create duplicate derived records.

The UI makes source text, generated synthesis, and backlog records visibly distinct.

Tests verify deterministic latest resolution and rejection of evidence-free backlog creation.

All state-changing actions are user-visible and user-initiated.

Suggested implementation sequence
A constrained order of build reduces drift.

Filesystem source registration and scanning.

Markdown parsing and metadata extraction.

Local database schema with idempotent ingestion behavior.

Keyword retrieval.

Evidence response model with provenance-constrained excerpts.

Deterministic related-notes endpoint.

Thread creation and pinning.

Thread summaries with non-evidence constraints.

Internal backlog item creation and status management.

Optional hybrid retrieval.

Hardening tests for boundaries, rebuild invariants, and non-goals.

Test cases
Retrieval tests
Query by exact title returns expected note.

Query by tag returns correct note subset.

latest ordering is deterministic when updated timestamps match.

Passing thread_id does not change results or ranking in v1.

Deleted or changed files are reflected after rescan.

Relatedness tests
Shared-tag related notes are labeled shared_tag.

Bidirectional wikilinks are labeled correctly.

Embedding-based relatedness appears only when enabled.

Thread tests
Evidence must be pinned explicitly before it appears in thread evidence state.

Thread summary survives app restart but remains editable.

Thread summary is not used as retrieval input.

Thread content cannot overwrite note content.

Backlog tests
Attempt to create backlog item without evidence fails.

Backlog item stores linked evidence IDs.

Confidence is stored but interpreted only as evidence-support strength.

Status changes are tracked locally.

No code path exists for external Jira calls in v1.

Boundary tests
Rebuild indexes after deleting local DB leaves source notes intact.

Repeated scans of unchanged files do not duplicate records.

Changed files replace prior derived records by identity and file hash.

Deleted files remove corresponding derived records.

Threads and backlog items remain separate from note records.

No state changes occur without explicit user action.

Open decisions for implementation
These decisions are still allowed at implementation time, provided they do not violate the invariants above:

SQLite or DuckDB for local persistence.

Exact chunking strategy.

Embedding model choice, if hybrid retrieval is enabled.

UI framework choice.

Filesystem watcher vs manual or scheduled rescan.

Final implementation instruction
Build exactly the constrained v1 system described here. Do not add external execution, note mutation, hidden memory behavior, implicit thread merging, evidence-free action generation, hidden query expansion, or invisible state mutation. When requirements are ambiguous, prefer preserving source-of-truth boundaries, deterministic behavior, and explicit user action over automation.
