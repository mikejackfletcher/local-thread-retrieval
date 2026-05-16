from __future__ import annotations

import os

from local_thread_retrieval.backlog import (
    create_backlog_item,
    get_backlog_item,
    list_backlog_evidence_links,
)
from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.evidence import create_evidence_from_chunk, get_evidence
from local_thread_retrieval.ingest import register_source, rescan_source
from local_thread_retrieval.invariants import (
    assert_invariants,
    deterministic_rebuild_snapshot,
    row_counts,
    source_derived_snapshot,
    validate_invariants,
)
from local_thread_retrieval.retrieval import search
from local_thread_retrieval.schema import SearchRequest
from local_thread_retrieval.threads import (
    create_thread,
    list_pinned_evidence,
    pin_evidence,
    store_thread_summary,
)


ALL_STATE_TABLES = (
    "notes",
    "note_metadata",
    "chunks",
    "links",
    "evidence",
    "threads",
    "thread_messages",
    "pinned_evidence",
    "thread_synthesis",
    "backlog_items",
    "backlog_evidence_links",
    "backlog_history",
)


def test_rebuild_from_scratch_produces_consistent_derived_state(tmp_path):
    source = _write_vault(tmp_path)

    first = deterministic_rebuild_snapshot(tmp_path / "first.db", source)
    second = deterministic_rebuild_snapshot(tmp_path / "second.db", source)

    assert first == second


def test_repeated_ingestion_remains_idempotent(tmp_path):
    source = _write_vault(tmp_path)
    connection = _indexed_connection(tmp_path / "local.db", source)
    first_snapshot = source_derived_snapshot(connection)

    for _ in range(3):
        rescan_source(connection, source)

    assert source_derived_snapshot(connection) == first_snapshot
    assert_invariants(connection)


def test_latest_sorting_is_deterministic(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "a.md").write_text(
        "---\ntitle: Alpha\nupdated: 2026-05-16T10:00:00+00:00\n---\n# Same\nneedle\n",
        encoding="utf-8",
    )
    (source / "b.md").write_text(
        "---\ntitle: Beta\nupdated: 2026-05-16T10:00:00+00:00\n---\n# Same\nneedle\n",
        encoding="utf-8",
    )
    fixed_mtime = 1_779_000_000
    os.utime(source / "a.md", (fixed_mtime, fixed_mtime))
    os.utime(source / "b.md", (fixed_mtime, fixed_mtime))
    connection = _indexed_connection(tmp_path / "local.db", source)
    request = SearchRequest(query_text="needle", sort_mode="latest")

    first = search(connection, request)
    second = search(connection, request)

    assert [result.path for result in first.results] == ["a.md", "b.md"]
    assert [result.evidence_id for result in first.results] == [
        result.evidence_id for result in second.results
    ]


def test_evidence_always_remains_traceable_to_source(tmp_path):
    connection, _source, _note, evidence_ids = _full_state(tmp_path)

    assert get_evidence(connection, evidence_ids[0]).path == "alpha.md"
    assert validate_invariants(connection) == []

    connection.execute(
        "UPDATE evidence SET path = 'not-the-source.md' WHERE evidence_id = ?",
        (evidence_ids[0],),
    )
    connection.commit()

    violations = validate_invariants(connection)
    assert [violation.name for violation in violations] == [
        "evidence_provenance_mismatch"
    ]


def test_deleted_files_correctly_remove_derived_records(tmp_path):
    source = _write_vault(tmp_path)
    connection = _indexed_connection(tmp_path / "local.db", source)
    chunk = connection.execute(
        "SELECT * FROM chunks WHERE heading = 'Alpha'"
    ).fetchone()
    create_evidence_from_chunk(connection, chunk["chunk_id"])

    (source / "alpha.md").unlink()
    rescan_source(connection, source)

    assert connection.execute(
        "SELECT COUNT(*) AS count FROM notes WHERE path = 'alpha.md'"
    ).fetchone()["count"] == 0
    assert connection.execute(
        "SELECT COUNT(*) AS count FROM chunks WHERE note_id NOT IN (SELECT note_id FROM notes)"
    ).fetchone()["count"] == 0
    assert connection.execute(
        "SELECT COUNT(*) AS count FROM links WHERE note_id NOT IN (SELECT note_id FROM notes)"
    ).fetchone()["count"] == 0
    assert connection.execute(
        "SELECT COUNT(*) AS count FROM evidence WHERE path = 'alpha.md'"
    ).fetchone()["count"] == 0
    assert_invariants(connection)


def test_retrieval_remains_independent_from_thread_id(tmp_path):
    connection, _source, _note, evidence_ids = _full_state(tmp_path)
    thread = create_thread(connection, "Retrieval invariant")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    store_thread_summary(connection, thread.thread_id, "Prefer beta only.")

    without_thread = search(connection, SearchRequest(query_text="alpha"))
    with_thread = search(
        connection,
        SearchRequest(query_text="alpha", thread_id=thread.thread_id),
    )

    assert [result.evidence_id for result in with_thread.results] == [
        result.evidence_id for result in without_thread.results
    ]
    assert [result.retrieval_score for result in with_thread.results] == [
        result.retrieval_score for result in without_thread.results
    ]


def test_no_hidden_state_mutation_occurs_on_read_operations(tmp_path):
    connection, _source, _note, evidence_ids = _full_state(tmp_path)
    thread = create_thread(connection, "Read-only checks")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    item = create_backlog_item(
        connection,
        title="Local item",
        description="Evidence-backed only.",
        evidence_ids=[evidence_ids[0]],
    )
    before = row_counts(connection, ALL_STATE_TABLES)

    search(connection, SearchRequest(query_text="alpha", thread_id=thread.thread_id))
    get_evidence(connection, evidence_ids[0])
    list_pinned_evidence(connection, thread.thread_id)
    get_backlog_item(connection, item.backlog_id)
    list_backlog_evidence_links(connection, item.backlog_id)
    validate_invariants(connection)

    assert row_counts(connection, ALL_STATE_TABLES) == before


def test_thread_summaries_are_never_treated_as_evidence(tmp_path):
    connection, _source, _note, evidence_ids = _full_state(tmp_path)
    thread = create_thread(connection, "Summary boundary")
    pin_evidence(connection, thread.thread_id, evidence_ids[0])
    summary = store_thread_summary(
        connection,
        thread.thread_id,
        "summary-only-hardening-token",
        evidence_ids=[evidence_ids[0]],
    )

    assert get_evidence(connection, summary.synthesis_id) is None
    assert search(
        connection,
        SearchRequest(query_text="summary-only-hardening-token"),
    ).results == []
    assert_invariants(connection)


def test_backlog_items_are_never_treated_as_source_truth(tmp_path):
    connection, _source, _note, evidence_ids = _full_state(tmp_path)
    item = create_backlog_item(
        connection,
        title="Backlog boundary",
        description="This remains local internal state.",
        evidence_ids=[evidence_ids[0]],
    )

    assert connection.execute(
        "SELECT COUNT(*) AS count FROM notes WHERE note_id = ?",
        (item.backlog_id,),
    ).fetchone()["count"] == 0
    assert get_evidence(connection, item.backlog_id) is None
    assert_invariants(connection)


def _write_vault(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "alpha.md").write_text(
        "---\ntitle: Alpha\nupdated: 2026-05-16T10:00:00+00:00\ntags: [work]\n---\n# Alpha\nalpha source text with [[Beta]].\n",
        encoding="utf-8",
    )
    (source / "beta.md").write_text(
        "---\ntitle: Beta\nupdated: 2026-05-15T10:00:00+00:00\ntags: [home]\n---\n# Beta\nbeta source text linking [Alpha](alpha.md).\n",
        encoding="utf-8",
    )
    return source


def _indexed_connection(database_path, source):
    connection = connect_database(database_path)
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    return connection


def _full_state(tmp_path):
    source = _write_vault(tmp_path)
    connection = _indexed_connection(tmp_path / "local.db", source)
    chunk_rows = connection.execute(
        "SELECT * FROM chunks ORDER BY chunk_index, chunk_id"
    ).fetchall()
    evidence_ids = [
        create_evidence_from_chunk(connection, row["chunk_id"]).evidence_id
        for row in chunk_rows
    ]
    return connection, source, source / "alpha.md", evidence_ids
