from __future__ import annotations

import json
import sqlite3
import uuid

from .schema import EvidenceRecord


NAMESPACE = uuid.UUID("691e3e64-aea2-4c7a-9a47-3832c45beb6f")
MAX_EXCERPT_LENGTH = 500
RETRIEVAL_MODES = {"keyword", "hybrid", "semantic"}


def create_evidence_from_chunk(
    connection: sqlite3.Connection,
    chunk_id: str,
    *,
    excerpt_start: int = 0,
    excerpt_end: int | None = None,
    retrieval_score: float = 0.0,
    retrieval_mode: str = "keyword",
) -> EvidenceRecord:
    if retrieval_mode not in RETRIEVAL_MODES:
        raise ValueError("retrieval_mode must be keyword, hybrid, or semantic")

    row = _chunk_with_note(connection, chunk_id)
    if row is None:
        raise ValueError(f"chunk does not exist: {chunk_id}")

    chunk_text = row["text"]
    requested_end = len(chunk_text) if excerpt_end is None else excerpt_end
    _validate_bounds(chunk_text, excerpt_start, requested_end)
    capped_end = min(requested_end, excerpt_start + MAX_EXCERPT_LENGTH)
    excerpt = chunk_text[excerpt_start:capped_end]
    evidence_id = _stable_id(
        "evidence",
        chunk_id,
        str(excerpt_start),
        str(capped_end),
        retrieval_mode,
        str(float(retrieval_score)),
    )

    connection.execute(
        """
        INSERT OR REPLACE INTO evidence (
            evidence_id, note_id, chunk_id, path, title, source_root,
            section_path, heading, excerpt, excerpt_char_start, excerpt_char_end,
            updated_at, file_mtime, retrieval_score, retrieval_mode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            row["note_id"],
            row["chunk_id"],
            row["path"],
            row["title"],
            row["source_root"],
            row["section_path"],
            row["heading"],
            excerpt,
            excerpt_start,
            capped_end,
            row["updated_at"],
            row["file_mtime"],
            float(retrieval_score),
            retrieval_mode,
        ),
    )
    connection.commit()
    return _record_from_row(
        connection.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
    )


def get_evidence(connection: sqlite3.Connection, evidence_id: str) -> EvidenceRecord | None:
    row = connection.execute(
        "SELECT * FROM evidence WHERE evidence_id = ?",
        (evidence_id,),
    ).fetchone()
    if row is None:
        return None
    return _record_from_row(row)


def _chunk_with_note(
    connection: sqlite3.Connection,
    chunk_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            chunks.chunk_id,
            chunks.note_id,
            chunks.section_path,
            chunks.heading,
            chunks.text,
            notes.path,
            notes.title,
            notes.source_root,
            notes.updated_at,
            notes.file_mtime
        FROM chunks
        JOIN notes ON notes.note_id = chunks.note_id
        WHERE chunks.chunk_id = ?
        """,
        (chunk_id,),
    ).fetchone()


def _validate_bounds(text: str, start: int, end: int) -> None:
    if start < 0:
        raise ValueError("excerpt_start must be greater than or equal to zero")
    if end <= start:
        raise ValueError("excerpt_end must be greater than excerpt_start")
    if end > len(text):
        raise ValueError("excerpt_end must be within the chunk text")


def _record_from_row(row: sqlite3.Row) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=row["evidence_id"],
        note_id=row["note_id"],
        chunk_id=row["chunk_id"],
        path=row["path"],
        title=row["title"],
        source_root=row["source_root"],
        section_path=json.loads(row["section_path"]),
        heading=row["heading"],
        excerpt=row["excerpt"],
        excerpt_char_start=row["excerpt_char_start"],
        excerpt_char_end=row["excerpt_char_end"],
        updated_at=row["updated_at"],
        file_mtime=row["file_mtime"],
        retrieval_score=row["retrieval_score"],
        retrieval_mode=row["retrieval_mode"],
    )


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "\x1f".join(parts)))
