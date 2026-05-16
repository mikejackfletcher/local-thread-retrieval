from __future__ import annotations

import hashlib
import sqlite3

import pytest

from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.evidence import create_evidence_from_chunk, get_evidence
from local_thread_retrieval.ingest import register_source, rescan_source


def test_evidence_can_be_created_only_from_existing_chunks(tmp_path):
    connection, _source, _note = _indexed_source(
        tmp_path,
        "# Evidence\nA real source sentence.\n",
    )

    with pytest.raises(ValueError, match="chunk does not exist"):
        create_evidence_from_chunk(connection, "missing-chunk-id")

    assert connection.execute("SELECT COUNT(*) AS count FROM evidence").fetchone()[
        "count"
    ] == 0


def test_evidence_excerpt_is_contiguous_source_text(tmp_path):
    connection, _source, _note = _indexed_source(
        tmp_path,
        "# Evidence\n0123456789 contiguous source text\n",
    )
    chunk = connection.execute("SELECT * FROM chunks").fetchone()

    evidence = create_evidence_from_chunk(
        connection,
        chunk["chunk_id"],
        excerpt_start=11,
        excerpt_end=21,
    )

    assert evidence.excerpt == chunk["text"][11:21]
    assert evidence.excerpt == "0123456789"
    assert evidence.excerpt_char_start == 11
    assert evidence.excerpt_char_end == 21
    assert get_evidence(connection, evidence.evidence_id) == evidence


def test_evidence_excerpts_are_capped_at_500_characters(tmp_path):
    long_text = "# Evidence\n" + ("a" * 700) + "\n"
    connection, _source, _note = _indexed_source(tmp_path, long_text)
    chunk = connection.execute("SELECT * FROM chunks").fetchone()

    evidence = create_evidence_from_chunk(connection, chunk["chunk_id"])

    assert len(evidence.excerpt) == 500
    assert evidence.excerpt == chunk["text"][:500]
    assert evidence.excerpt_char_start == 0
    assert evidence.excerpt_char_end == 500


def test_evidence_records_preserve_note_and_chunk_provenance(tmp_path):
    connection, source, _note = _indexed_source(
        tmp_path,
        "---\ntitle: Source Note\nupdated: 2026-05-16T10:00:00+00:00\n---\n# Parent\nIgnore.\n\n## Child\nEvidence text.\n",
    )
    chunk = connection.execute(
        "SELECT * FROM chunks WHERE heading = 'Child'"
    ).fetchone()
    note = connection.execute("SELECT * FROM notes").fetchone()

    evidence = create_evidence_from_chunk(
        connection,
        chunk["chunk_id"],
        retrieval_score=2.5,
        retrieval_mode="keyword",
    )

    assert evidence.note_id == note["note_id"]
    assert evidence.chunk_id == chunk["chunk_id"]
    assert evidence.path == "note.md"
    assert evidence.title == "Source Note"
    assert evidence.source_root == str(source.resolve())
    assert evidence.section_path == ["Parent", "Child"]
    assert evidence.heading == "Child"
    assert evidence.updated_at == "2026-05-16T10:00:00+00:00"
    assert evidence.file_mtime == note["file_mtime"]
    assert evidence.retrieval_score == 2.5
    assert evidence.retrieval_mode == "keyword"


def test_generated_free_text_cannot_be_stored_as_evidence(tmp_path):
    connection, _source, _note = _indexed_source(
        tmp_path,
        "# Evidence\nActual source text.\n",
    )
    chunk = connection.execute("SELECT * FROM chunks").fetchone()
    note = connection.execute("SELECT * FROM notes").fetchone()

    with pytest.raises(sqlite3.IntegrityError, match="contiguous chunk text"):
        connection.execute(
            """
            INSERT INTO evidence (
                evidence_id, note_id, chunk_id, path, title, source_root,
                section_path, heading, excerpt, excerpt_char_start, excerpt_char_end,
                updated_at, file_mtime, retrieval_score, retrieval_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "generated-evidence",
                note["note_id"],
                chunk["chunk_id"],
                note["path"],
                note["title"],
                note["source_root"],
                chunk["section_path"],
                chunk["heading"],
                "Generated text that is not in the chunk.",
                0,
                40,
                note["updated_at"],
                note["file_mtime"],
                0.0,
                "keyword",
            ),
        )

    assert connection.execute("SELECT COUNT(*) AS count FROM evidence").fetchone()[
        "count"
    ] == 0


def test_evidence_creation_never_mutates_source_files(tmp_path):
    source_text = "# Evidence\nActual source text.\n"
    connection, _source, note = _indexed_source(tmp_path, source_text)
    before_hash = hashlib.sha256(note.read_bytes()).hexdigest()
    before_stat = note.stat()
    chunk = connection.execute("SELECT * FROM chunks").fetchone()

    create_evidence_from_chunk(connection, chunk["chunk_id"])

    assert note.read_text(encoding="utf-8") == source_text
    assert hashlib.sha256(note.read_bytes()).hexdigest() == before_hash
    assert note.stat().st_mtime_ns == before_stat.st_mtime_ns


def _indexed_source(tmp_path, text: str):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text(text, encoding="utf-8")
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    return connection, source, note
