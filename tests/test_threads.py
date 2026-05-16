from __future__ import annotations

import hashlib

import pytest

from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.evidence import create_evidence_from_chunk
from local_thread_retrieval.ingest import register_source, rescan_source
from local_thread_retrieval.retrieval import search
from local_thread_retrieval.schema import SearchRequest
from local_thread_retrieval.threads import (
    add_thread_message,
    create_thread,
    get_thread,
    list_pinned_evidence,
    list_thread_messages,
    pin_evidence,
    store_thread_summary,
)


def test_thread_creation(tmp_path):
    connection, _source, _note, _evidence_ids = _thread_fixture(tmp_path)

    thread = create_thread(
        connection,
        "Working context",
        created_at="2026-05-16T10:00:00+00:00",
    )

    assert thread.title == "Working context"
    assert thread.created_at == "2026-05-16T10:00:00+00:00"
    assert thread.updated_at == "2026-05-16T10:00:00+00:00"
    assert thread.status == "active"
    assert thread.summary is None
    assert get_thread(connection, thread.thread_id) == thread


def test_add_messages_to_thread(tmp_path):
    connection, _source, _note, _evidence_ids = _thread_fixture(tmp_path)
    thread = create_thread(
        connection,
        "Message context",
        created_at="2026-05-16T10:00:00+00:00",
    )

    first = add_thread_message(
        connection,
        thread.thread_id,
        "user",
        "What matters here?",
        created_at="2026-05-16T10:01:00+00:00",
    )
    second = add_thread_message(
        connection,
        thread.thread_id,
        "assistant",
        "Only pinned evidence matters.",
        created_at="2026-05-16T10:02:00+00:00",
    )

    assert first.thread_id == thread.thread_id
    assert second.role == "assistant"
    assert list_thread_messages(connection, thread.thread_id) == [first, second]
    assert get_thread(connection, thread.thread_id).updated_at == (
        "2026-05-16T10:02:00+00:00"
    )


def test_pinning_existing_evidence_only(tmp_path):
    connection, _source, _note, evidence_ids = _thread_fixture(tmp_path)
    thread = create_thread(connection, "Pin context")

    with pytest.raises(ValueError, match="evidence does not exist"):
        pin_evidence(connection, thread.thread_id, "missing-evidence-id")

    pin = pin_evidence(
        connection,
        thread.thread_id,
        evidence_ids[0],
        pin_reason="Relevant source quote",
        pinned_at="2026-05-16T10:03:00+00:00",
    )

    assert pin.thread_id == thread.thread_id
    assert pin.evidence_id == evidence_ids[0]
    assert pin.pin_reason == "Relevant source quote"
    assert list_pinned_evidence(connection, thread.thread_id) == [pin]


def test_summaries_are_stored_but_not_treated_as_evidence(tmp_path):
    connection, _source, _note, evidence_ids = _thread_fixture(tmp_path)
    thread = create_thread(connection, "Summary context")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    before_count = connection.execute(
        "SELECT COUNT(*) AS count FROM evidence"
    ).fetchone()["count"]

    summary = store_thread_summary(
        connection,
        thread.thread_id,
        "summary-only-token",
        evidence_ids=[evidence_ids[0]],
        created_at="2026-05-16T10:04:00+00:00",
    )

    assert summary.content == "summary-only-token"
    assert summary.evidence_ids == [evidence_ids[0]]
    assert get_thread(connection, thread.thread_id).summary == "summary-only-token"
    assert connection.execute("SELECT COUNT(*) AS count FROM evidence").fetchone()[
        "count"
    ] == before_count
    assert search(connection, SearchRequest(query_text="summary-only-token")).results == []


def test_retrieval_remains_independent_of_thread_id(tmp_path):
    connection, _source, _note, evidence_ids = _thread_fixture(tmp_path)
    thread = create_thread(connection, "Retrieval context")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    store_thread_summary(connection, thread.thread_id, "Prefer beta.")

    without_thread = search(connection, SearchRequest(query_text="alpha"))
    with_thread = search(
        connection,
        SearchRequest(query_text="alpha", thread_id=thread.thread_id),
    )

    assert [result.evidence_id for result in with_thread.results] == [
        result.evidence_id for result in without_thread.results
    ]
    assert [result.path for result in with_thread.results] == [
        result.path for result in without_thread.results
    ]


def test_evidence_does_not_leak_across_threads(tmp_path):
    connection, _source, _note, evidence_ids = _thread_fixture(tmp_path)
    alpha_thread = create_thread(connection, "Alpha thread")
    beta_thread = create_thread(connection, "Beta thread")

    alpha_pin = pin_evidence(connection, alpha_thread.thread_id, evidence_ids[0])
    beta_pin = pin_evidence(connection, beta_thread.thread_id, evidence_ids[1])

    assert list_pinned_evidence(connection, alpha_thread.thread_id) == [alpha_pin]
    assert list_pinned_evidence(connection, beta_thread.thread_id) == [beta_pin]
    assert alpha_pin.evidence_id != beta_pin.evidence_id


def test_thread_actions_never_mutate_source_files(tmp_path):
    connection, _source, note, evidence_ids = _thread_fixture(tmp_path)
    before_hash = hashlib.sha256(note.read_bytes()).hexdigest()
    before_stat = note.stat()
    thread = create_thread(connection, "Source boundary")

    add_thread_message(connection, thread.thread_id, "user", "Keep source read-only.")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    store_thread_summary(connection, thread.thread_id, "Stored locally only.")

    assert hashlib.sha256(note.read_bytes()).hexdigest() == before_hash
    assert note.stat().st_mtime_ns == before_stat.st_mtime_ns


def _thread_fixture(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text(
        "---\ntitle: Thread Source\n---\n# Alpha\nalpha source text\n\n# Beta\nbeta source text\n",
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
    return connection, source, note, evidence_ids
