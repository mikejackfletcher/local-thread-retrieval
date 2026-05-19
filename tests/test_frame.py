from __future__ import annotations

import hashlib

from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.evidence import create_evidence_from_chunk
from local_thread_retrieval.frame import assemble_chatgpt_frame
from local_thread_retrieval.ingest import register_source, rescan_source
from local_thread_retrieval.retrieval import search
from local_thread_retrieval.schema import SearchRequest
from local_thread_retrieval.threads import (
    add_thread_message,
    create_thread,
    pin_evidence,
    store_thread_summary,
)


def test_chatgpt_frame_output_is_deterministic(tmp_path):
    connection, _source, _note, thread_id, evidence_ids = _frame_fixture(tmp_path)
    results = search(connection, SearchRequest(query_text="alpha")).results

    first = assemble_chatgpt_frame(
        connection,
        retrieval_results=results,
        evidence_ids=evidence_ids,
        thread_id=thread_id,
    )
    second = assemble_chatgpt_frame(
        connection,
        retrieval_results=results,
        evidence_ids=evidence_ids,
        thread_id=thread_id,
    )

    assert first == second
    assert first.startswith("CHATGPT CONTEXT FRAME\n")


def test_chatgpt_frame_includes_provenance(tmp_path):
    connection, source, _note, thread_id, evidence_ids = _frame_fixture(tmp_path)
    result = search(connection, SearchRequest(query_text="alpha")).results[0]

    frame = assemble_chatgpt_frame(
        connection,
        retrieval_results=[result],
        evidence_ids=[evidence_ids[0]],
        thread_id=thread_id,
    )

    assert f"Note ID: {result.note_id}" in frame
    assert f"Chunk ID: {result.chunk_id}" in frame
    assert "Path: note.md" in frame
    assert f"Source root: {source.resolve()}" in frame
    assert f"Provenance source_root: {source.resolve()}" in frame
    assert "Provenance heading: Alpha" in frame
    assert 'Section path: ["Alpha"]' in frame


def test_chatgpt_frame_labels_summaries_as_summaries_not_evidence(tmp_path):
    connection, _source, _note, thread_id, evidence_ids = _frame_fixture(tmp_path)

    frame = assemble_chatgpt_frame(
        connection,
        evidence_ids=[evidence_ids[0]],
        thread_id=thread_id,
    )

    assert "THREAD SUMMARIES (NOT EVIDENCE)" in frame
    assert "Summary content:" in frame
    assert "summary-only-frame-token" in frame
    summary_section = frame.split("THREAD SUMMARIES (NOT EVIDENCE)", 1)[1].split(
        "PINNED EVIDENCE REFERENCES",
        1,
    )[0]
    evidence_section = frame.split("EVIDENCE RECORDS", 1)[1]
    assert "summary-only-frame-token" in summary_section
    assert "summary-only-frame-token" not in evidence_section


def test_chatgpt_frame_evidence_excerpts_remain_bounded(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "long.md"
    note.write_text("# Long\n" + ("a" * 700) + "\n", encoding="utf-8")
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    chunk_id = connection.execute("SELECT chunk_id FROM chunks").fetchone()["chunk_id"]
    evidence = create_evidence_from_chunk(connection, chunk_id)

    frame = assemble_chatgpt_frame(connection, evidence_ids=[evidence.evidence_id])

    assert len(evidence.excerpt) == 500
    assert "Excerpt character range: 0:500" in frame
    assert ("a" * 600) not in frame


def test_chatgpt_frame_assembly_never_mutates_source_files(tmp_path):
    connection, _source, note, thread_id, evidence_ids = _frame_fixture(tmp_path)
    before_hash = hashlib.sha256(note.read_bytes()).hexdigest()
    before_stat = note.stat()
    results = search(connection, SearchRequest(query_text="alpha")).results

    assemble_chatgpt_frame(
        connection,
        retrieval_results=results,
        evidence_ids=evidence_ids,
        thread_id=thread_id,
    )

    assert hashlib.sha256(note.read_bytes()).hexdigest() == before_hash
    assert note.stat().st_mtime_ns == before_stat.st_mtime_ns


def _frame_fixture(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text(
        "---\ntitle: Frame Source\nupdated: 2026-05-16T10:00:00+00:00\ntags: [frame]\n---\n# Alpha\nalpha source text\n\n# Beta\nbeta source text\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    chunks = connection.execute(
        "SELECT * FROM chunks ORDER BY chunk_index"
    ).fetchall()
    evidence_ids = [
        create_evidence_from_chunk(connection, chunk["chunk_id"]).evidence_id
        for chunk in chunks
    ]
    thread = create_thread(
        connection,
        "Frame thread",
        created_at="2026-05-16T10:00:00+00:00",
    )
    add_thread_message(
        connection,
        thread.thread_id,
        "user",
        "Please consider selected evidence.",
        created_at="2026-05-16T10:01:00+00:00",
    )
    pin_evidence(
        connection,
        thread.thread_id,
        evidence_ids[0],
        pin_reason="Relevant excerpt",
        pinned_at="2026-05-16T10:02:00+00:00",
    )
    store_thread_summary(
        connection,
        thread.thread_id,
        "summary-only-frame-token",
        evidence_ids=[evidence_ids[0]],
        created_at="2026-05-16T10:03:00+00:00",
    )
    return connection, source, note, thread.thread_id, evidence_ids
