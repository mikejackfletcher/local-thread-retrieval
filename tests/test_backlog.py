from __future__ import annotations

import hashlib

import pytest

from local_thread_retrieval.backlog import (
    create_backlog_item,
    get_backlog_item,
    list_backlog_evidence_links,
    list_backlog_history,
    transition_backlog_status,
)
from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.evidence import create_evidence_from_chunk, get_evidence
from local_thread_retrieval.ingest import register_source, rescan_source


def test_backlog_item_creation_requires_evidence(tmp_path):
    connection, _source, _note, evidence_ids = _backlog_fixture(tmp_path)

    item = create_backlog_item(
        connection,
        title="Review source",
        description="Review the evidence-backed note.",
        evidence_ids=[evidence_ids[0]],
        priority="high",
        action_type="review",
        confidence=0.75,
        created_at="2026-05-16T10:00:00+00:00",
    )

    assert item.status == "proposed"
    assert item.priority == "high"
    assert item.action_type == "review"
    assert item.confidence == 0.75
    assert item.requires_confirmation is True
    assert get_backlog_item(connection, item.backlog_id) == item


def test_backlog_item_links_to_evidence(tmp_path):
    connection, _source, _note, evidence_ids = _backlog_fixture(tmp_path)

    item = create_backlog_item(
        connection,
        title="Follow up",
        description="Follow up using linked evidence.",
        evidence_ids=evidence_ids,
        created_at="2026-05-16T10:00:00+00:00",
    )

    links = list_backlog_evidence_links(connection, item.backlog_id)
    assert {link.evidence_id for link in links} == set(evidence_ids)
    assert {link.link_type for link in links} == {"primary", "supporting"}
    assert links[0].backlog_id == item.backlog_id


def test_evidence_free_backlog_creation_fails(tmp_path):
    connection, _source, _note, _evidence_ids = _backlog_fixture(tmp_path)

    with pytest.raises(ValueError, match="requires at least one evidence"):
        create_backlog_item(
            connection,
            title="Unsupported item",
            description="No evidence.",
            evidence_ids=[],
        )

    assert connection.execute("SELECT COUNT(*) AS count FROM backlog_items").fetchone()[
        "count"
    ] == 0


def test_valid_status_transitions_work(tmp_path):
    connection, _source, _note, evidence_ids = _backlog_fixture(tmp_path)
    item = create_backlog_item(
        connection,
        title="Transition item",
        description="Move through explicit statuses.",
        evidence_ids=[evidence_ids[0]],
        created_at="2026-05-16T10:00:00+00:00",
    )

    for index, status in enumerate(["triaged", "ready", "done", "dropped"], start=1):
        item = transition_backlog_status(
            connection,
            item.backlog_id,
            status,
            changed_at=f"2026-05-16T10:0{index}:00+00:00",
        )
        assert item.status == status

    history = list_backlog_history(connection, item.backlog_id)
    assert [entry.to_status for entry in history] == [
        "proposed",
        "triaged",
        "ready",
        "done",
        "dropped",
    ]


def test_invalid_status_transition_fails(tmp_path):
    connection, _source, _note, evidence_ids = _backlog_fixture(tmp_path)
    item = create_backlog_item(
        connection,
        title="Invalid transition item",
        description="Reject unknown statuses.",
        evidence_ids=[evidence_ids[0]],
    )

    with pytest.raises(ValueError, match="status must be"):
        transition_backlog_status(connection, item.backlog_id, "blocked")

    assert get_backlog_item(connection, item.backlog_id).status == "proposed"


def test_backlog_items_are_not_treated_as_evidence(tmp_path):
    connection, _source, _note, evidence_ids = _backlog_fixture(tmp_path)
    before_count = connection.execute(
        "SELECT COUNT(*) AS count FROM evidence"
    ).fetchone()["count"]

    item = create_backlog_item(
        connection,
        title="Evidence boundary",
        description="This backlog text is not evidence.",
        evidence_ids=[evidence_ids[0]],
    )

    assert get_evidence(connection, item.backlog_id) is None
    assert connection.execute("SELECT COUNT(*) AS count FROM evidence").fetchone()[
        "count"
    ] == before_count


def test_backlog_actions_never_mutate_source_files(tmp_path):
    connection, _source, note, evidence_ids = _backlog_fixture(tmp_path)
    before_hash = hashlib.sha256(note.read_bytes()).hexdigest()
    before_stat = note.stat()
    item = create_backlog_item(
        connection,
        title="Source boundary",
        description="Keep source markdown untouched.",
        evidence_ids=[evidence_ids[0]],
    )

    transition_backlog_status(connection, item.backlog_id, "triaged")

    assert hashlib.sha256(note.read_bytes()).hexdigest() == before_hash
    assert note.stat().st_mtime_ns == before_stat.st_mtime_ns


def _backlog_fixture(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    note = source / "note.md"
    note.write_text(
        "# Alpha\nalpha source text\n\n# Beta\nbeta source text\n",
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
