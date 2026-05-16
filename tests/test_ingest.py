from __future__ import annotations

import hashlib

from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.ingest import register_source, rescan_source


def test_ingestion_is_idempotent(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "note.md").write_text(
        "---\ntitle: Alpha\nupdated: 2026-05-16T10:00:00+00:00\ntags: [work]\n---\n# Heading\nBody with [[Beta]].\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)

    register_source(connection, source)
    rescan_source(connection, source)
    first_counts = _counts(connection)
    first_note_id = connection.execute("SELECT note_id FROM notes").fetchone()["note_id"]
    first_chunk_ids = [
        row["chunk_id"]
        for row in connection.execute("SELECT chunk_id FROM chunks ORDER BY chunk_index")
    ]

    rescan_source(connection, source)

    assert _counts(connection) == first_counts
    assert connection.execute("SELECT note_id FROM notes").fetchone()["note_id"] == first_note_id
    assert [
        row["chunk_id"]
        for row in connection.execute("SELECT chunk_id FROM chunks ORDER BY chunk_index")
    ] == first_chunk_ids


def test_repeated_scan_does_not_duplicate_derived_records(tmp_path):
    source = tmp_path / "vault"
    nested = source / "folder"
    nested.mkdir(parents=True)
    (source / "alpha.md").write_text("# Alpha\n#tag [[Beta]]\n", encoding="utf-8")
    (nested / "beta.md").write_text("# Beta\nBacklink [[Alpha]]\n", encoding="utf-8")
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)

    register_source(connection, source)
    for _ in range(3):
        rescan_source(connection, source)

    assert _counts(connection) == {
        "notes": 2,
        "chunks": 2,
        "links": 2,
        "evidence": 0,
    }


def test_ingestion_does_not_mutate_source_files(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    original = "---\ntitle: Keep Me\n---\n# Original\nUnchanged text.\n"
    note.write_text(original, encoding="utf-8")
    before_hash = hashlib.sha256(note.read_bytes()).hexdigest()
    before_stat = note.stat()
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)

    register_source(connection, source)
    rescan_source(connection, source)

    assert note.read_text(encoding="utf-8") == original
    assert hashlib.sha256(note.read_bytes()).hexdigest() == before_hash
    assert note.stat().st_mtime_ns == before_stat.st_mtime_ns


def _counts(connection):
    return {
        table: connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()[
            "count"
        ]
        for table in ("notes", "chunks", "links", "evidence")
    }
