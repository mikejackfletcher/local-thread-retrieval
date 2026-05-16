from __future__ import annotations

import hashlib
import json

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
    (source / "alpha.md").write_text(
        "# Alpha\n#tag [[Beta]] [Beta File](folder/beta.md)\n", encoding="utf-8"
    )
    (nested / "beta.md").write_text("# Beta\nBacklink [[Alpha]]\n", encoding="utf-8")
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)

    register_source(connection, source)
    for _ in range(3):
        rescan_source(connection, source)

    assert _counts(connection) == {
        "notes": 2,
        "chunks": 2,
        "links": 3,
        "evidence": 0,
    }


def test_changed_source_updates_derived_records_deterministically(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text(
        "---\ntitle: Original\nupdated: 2026-05-16T10:00:00+00:00\ntags: [alpha]\n---\n# One\nOld [[Target]].\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    original_note = connection.execute("SELECT * FROM notes").fetchone()
    original_chunk = connection.execute("SELECT * FROM chunks").fetchone()
    original_link_id = connection.execute("SELECT link_id FROM links").fetchone()[
        "link_id"
    ]

    note.write_text(
        "---\ntitle: Updated\nupdated: 2026-05-16T11:00:00+00:00\ntags: [beta]\n---\n# One\nNew [[Other]].\n\n## Two\nSecond section.\n",
        encoding="utf-8",
    )
    rescan_source(connection, source)

    updated_note = connection.execute("SELECT * FROM notes").fetchone()
    chunks = connection.execute(
        "SELECT * FROM chunks ORDER BY chunk_index"
    ).fetchall()
    links = connection.execute("SELECT * FROM links").fetchall()

    assert updated_note["note_id"] == original_note["note_id"]
    assert updated_note["title"] == "Updated"
    assert updated_note["file_hash"] != original_note["file_hash"]
    assert json.loads(updated_note["tags"]) == ["beta"]
    assert len(chunks) == 2
    assert chunks[0]["chunk_id"] == original_chunk["chunk_id"]
    assert chunks[0]["text"] == "# One\nNew [[Other]]."
    assert chunks[1]["heading"] == "Two"
    assert len(links) == 1
    assert links[0]["target"] == "Other"
    assert links[0]["link_id"] != original_link_id


def test_removed_source_deletes_derived_records(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text("---\ntitle: Gone\n---\n# Gone\n[[Target]]\n", encoding="utf-8")
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)

    note.unlink()
    rescan_source(connection, source)

    assert _counts(connection) == {
        "notes": 0,
        "chunks": 0,
        "links": 0,
        "evidence": 0,
    }
    assert connection.execute("SELECT COUNT(*) AS count FROM note_metadata").fetchone()[
        "count"
    ] == 0


def test_provenance_metadata_is_preserved(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "note.md").write_text(
        "---\ntitle: Provenance\ncreated: 2026-05-15T09:00:00+00:00\nupdated: 2026-05-16T10:00:00+00:00\ntags: [source]\n---\nIntro text.\n\n# Parent\nText.\n\n## Child\nMore text with [[Target]].\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    registered_root = register_source(connection, source)
    rescan_source(connection, source)

    note = connection.execute("SELECT * FROM notes").fetchone()
    chunks = connection.execute(
        "SELECT * FROM chunks ORDER BY chunk_index"
    ).fetchall()

    assert note["source_root"] == registered_root
    assert note["path"] == "note.md"
    assert note["title"] == "Provenance"
    assert note["created_at"] == "2026-05-15T09:00:00+00:00"
    assert note["updated_at"] == "2026-05-16T10:00:00+00:00"
    assert note["file_mtime"]
    assert len(note["file_hash"]) == 64
    assert json.loads(chunks[0]["section_path"]) == []
    assert chunks[0]["heading"] is None
    assert chunks[0]["text"] == "Intro text."
    assert json.loads(chunks[1]["section_path"]) == ["Parent"]
    assert chunks[1]["heading"] == "Parent"
    assert json.loads(chunks[2]["section_path"]) == ["Parent", "Child"]
    assert chunks[2]["heading"] == "Child"
    assert chunks[2]["char_start"] < chunks[2]["char_end"]


def test_source_files_are_never_mutated(tmp_path):
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
