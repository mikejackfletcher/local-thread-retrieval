from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ParsedChunk:
    section_path: list[str]
    heading: str | None
    text: str
    char_start: int
    char_end: int
    chunk_index: int
    retrieval_text: str


@dataclass(frozen=True)
class ParsedLink:
    target: str
    link_type: str


@dataclass(frozen=True)
class ParsedNote:
    title: str
    front_matter: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    links: list[ParsedLink] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    body: str = ""
    chunks: list[ParsedChunk] = field(default_factory=list)
    parse_status: str = "ok"


@dataclass(frozen=True)
class SearchRequest:
    query_text: str
    thread_id: str | None = None
    filters: dict[str, list[str]] = field(default_factory=dict)
    sort_mode: str = "relevance"
    limit: int = 10


@dataclass(frozen=True)
class SearchResult:
    evidence_id: str
    note_id: str
    chunk_id: str
    title: str
    path: str
    section_path: list[str]
    excerpt: str
    retrieval_score: float
    retrieval_mode: str
    updated_at: str | None
    file_mtime: str
    provenance: dict[str, str | None]
    score_explanation: dict[str, float]
    sort_fields: dict[str, str | None]


@dataclass(frozen=True)
class SearchResponse:
    query_id: str
    results: list[SearchResult]


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    note_id: str
    chunk_id: str
    path: str
    title: str
    source_root: str
    section_path: list[str]
    heading: str | None
    excerpt: str
    excerpt_char_start: int
    excerpt_char_end: int
    updated_at: str | None
    file_mtime: str
    retrieval_score: float
    retrieval_mode: str


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    status: str
    summary: str | None = None


@dataclass(frozen=True)
class ThreadMessageRecord:
    message_id: str
    thread_id: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class PinnedEvidenceRecord:
    pin_id: str
    thread_id: str
    evidence_id: str
    pinned_at: str
    pin_reason: str | None = None


@dataclass(frozen=True)
class ThreadSummaryRecord:
    synthesis_id: str
    thread_id: str
    content: str
    evidence_ids: list[str]
    created_at: str
