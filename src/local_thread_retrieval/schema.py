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
