from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections import Counter

from .schema import RelatedNoteResult, SearchRequest, SearchResponse, SearchResult


NAMESPACE = uuid.UUID("1536ae6f-1142-49a4-b9d7-64fd34a7e4e9")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
MAX_EXCERPT_LENGTH = 500
FIELD_WEIGHTS = {
    "title": 4.0,
    "tags": 3.0,
    "front_matter": 2.0,
    "chunk_text": 1.0,
}
RELATION_TYPE_ORDER = ("shared_wikilink", "backlink", "shared_tag")


def search(connection: sqlite3.Connection, request: SearchRequest) -> SearchResponse:
    if request.sort_mode not in {"relevance", "latest"}:
        raise ValueError("sort_mode must be 'relevance' or 'latest'")
    if request.limit < 1:
        raise ValueError("limit must be greater than zero")

    query_tokens = _tokenize(request.query_text)
    query_id = _stable_id(
        "query",
        request.query_text,
        request.sort_mode,
        json.dumps(request.filters, sort_keys=True, separators=(",", ":")),
        str(request.limit),
    )
    if not query_tokens:
        return SearchResponse(query_id=query_id, results=[])

    candidates = []
    for row in _candidate_rows(connection):
        if not _matches_filters(row, request.filters):
            continue

        explanation = _score_row(row, query_tokens)
        score = sum(explanation.values())
        if score <= 0:
            continue

        candidates.append(
            _result_from_row(
                row=row,
                score=score,
                explanation=explanation,
            )
        )

    if request.sort_mode == "latest":
        candidates.sort(
            key=lambda result: (
                -result.retrieval_score,
                result.updated_at is None,
                _descending_text(result.updated_at or ""),
                _descending_text(result.file_mtime),
                result.path,
                result.provenance["heading"] or "",
                result.chunk_id,
            )
        )
    else:
        candidates.sort(
            key=lambda result: (
                -result.retrieval_score,
                result.path,
                result.provenance["heading"] or "",
                result.chunk_id,
            )
        )

    return SearchResponse(query_id=query_id, results=candidates[: request.limit])


def related_notes(
    connection: sqlite3.Connection,
    note_id: str,
    *,
    limit: int = 10,
) -> list[RelatedNoteResult]:
    if limit < 1:
        raise ValueError("limit must be greater than zero")
    source = _note_row(connection, note_id)
    if source is None:
        raise ValueError(f"note does not exist: {note_id}")

    source_tags = set(json.loads(source["tags"]))
    source_wikilinks = set(json.loads(source["wikilinks"]))
    source_link_targets = {
        source["title"],
        source["path"],
        source["path"].rsplit(".", 1)[0],
    }
    results: list[RelatedNoteResult] = []
    for candidate in connection.execute(
        """
        SELECT note_id, path, title, tags, wikilinks
        FROM notes
        WHERE note_id != ? AND parse_status = 'ok'
        ORDER BY path
        """,
        (note_id,),
    ).fetchall():
        candidate_tags = set(json.loads(candidate["tags"]))
        candidate_wikilinks = set(json.loads(candidate["wikilinks"]))
        relation_types: list[str] = []
        score = 0.0

        shared_wikilinks = source_wikilinks.intersection(candidate_wikilinks)
        if shared_wikilinks:
            relation_types.append("shared_wikilink")
            score += 2.0 * len(shared_wikilinks)

        if candidate_wikilinks.intersection(source_link_targets):
            relation_types.append("backlink")
            score += 3.0

        shared_tags = source_tags.intersection(candidate_tags)
        if shared_tags:
            relation_types.append("shared_tag")
            score += 1.0 * len(shared_tags)

        if relation_types:
            results.append(
                RelatedNoteResult(
                    related_note_id=candidate["note_id"],
                    path=candidate["path"],
                    title=candidate["title"],
                    relation_types=[
                        relation_type
                        for relation_type in RELATION_TYPE_ORDER
                        if relation_type in relation_types
                    ],
                    relation_score=score,
                )
            )

    results.sort(
        key=lambda result: (
            -result.relation_score,
            result.path,
            result.related_note_id,
        )
    )
    return results[:limit]


def _candidate_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            notes.note_id,
            notes.source_root,
            notes.path,
            notes.title,
            notes.front_matter,
            notes.tags,
            notes.updated_at,
            notes.file_mtime,
            chunks.chunk_id,
            chunks.section_path,
            chunks.heading,
            chunks.text
        FROM chunks
        JOIN notes ON notes.note_id = chunks.note_id
        WHERE notes.parse_status = 'ok'
        ORDER BY notes.path, chunks.chunk_index
        """
    ).fetchall()


def _note_row(connection: sqlite3.Connection, note_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT note_id, path, title, tags, wikilinks
        FROM notes
        WHERE note_id = ? AND parse_status = 'ok'
        """,
        (note_id,),
    ).fetchone()


def _score_row(row: sqlite3.Row, query_tokens: list[str]) -> dict[str, float]:
    fields = {
        "title": row["title"],
        "tags": " ".join(json.loads(row["tags"])),
        "front_matter": _front_matter_text(row["front_matter"]),
        "chunk_text": row["text"],
    }
    explanation: dict[str, float] = {}
    for field, text in fields.items():
        matches = _match_count(text, query_tokens)
        if matches:
            explanation[field] = matches * FIELD_WEIGHTS[field]
    return explanation


def _result_from_row(
    row: sqlite3.Row,
    score: float,
    explanation: dict[str, float],
) -> SearchResult:
    section_path = json.loads(row["section_path"])
    excerpt = _excerpt(row["text"])
    return SearchResult(
        evidence_id=_stable_id("evidence", row["chunk_id"]),
        note_id=row["note_id"],
        chunk_id=row["chunk_id"],
        title=row["title"],
        path=row["path"],
        section_path=section_path,
        excerpt=excerpt,
        retrieval_score=score,
        retrieval_mode="keyword",
        updated_at=row["updated_at"],
        file_mtime=row["file_mtime"],
        provenance={
            "source_root": row["source_root"],
            "heading": row["heading"],
        },
        score_explanation=explanation,
        sort_fields={
            "updated_at": row["updated_at"],
            "file_mtime": row["file_mtime"],
            "path": row["path"],
        },
    )


def _matches_filters(row: sqlite3.Row, filters: dict[str, list[str]]) -> bool:
    tags_any = filters.get("tags_any") or []
    if tags_any:
        tags = set(json.loads(row["tags"]))
        if not tags.intersection(tags_any):
            return False

    source_roots = filters.get("source_roots") or []
    if source_roots and row["source_root"] not in source_roots:
        return False

    paths_prefix = filters.get("paths_prefix") or []
    if paths_prefix and not any(row["path"].startswith(prefix) for prefix in paths_prefix):
        return False

    return True


def _front_matter_text(front_matter_json: str) -> str:
    loaded = json.loads(front_matter_json)
    for already_scored_key in ("title", "tags"):
        loaded.pop(already_scored_key, None)
    return json.dumps(loaded, sort_keys=True, separators=(" ", " "))


def _match_count(text: str, query_tokens: list[str]) -> int:
    counts = Counter(_tokenize(text))
    return sum(counts[token] for token in query_tokens)


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _excerpt(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= MAX_EXCERPT_LENGTH:
        return stripped
    return stripped[: MAX_EXCERPT_LENGTH - 3].rstrip() + "..."


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "\x1f".join(parts)))


def _descending_text(value: str) -> tuple[int, ...]:
    return tuple(-ord(character) for character in value)
