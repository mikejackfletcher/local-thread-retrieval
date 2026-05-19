from __future__ import annotations

from dataclasses import asdict

from local_thread_retrieval.db import connect_database, init_database
from local_thread_retrieval.ingest import register_source, rescan_source
from local_thread_retrieval.retrieval import related_notes, search
from local_thread_retrieval.schema import SearchRequest


def test_keyword_search_has_deterministic_ranking_order(tmp_path):
    connection = _indexed_vault(tmp_path)

    response = search(connection, SearchRequest(query_text="alpha"))

    assert [result.path for result in response.results] == [
        "title.md",
        "tags.md",
        "front.md",
        "chunk.md",
    ]
    assert [result.retrieval_score for result in response.results] == [
        4.0,
        3.0,
        2.0,
        1.0,
    ]
    assert response.results[0].score_explanation == {"title": 4.0}
    assert response.results[1].score_explanation == {"tags": 3.0}
    assert response.results[2].score_explanation == {"front_matter": 2.0}
    assert response.results[3].score_explanation == {"chunk_text": 1.0}


def test_latest_sorting_uses_spec_tie_break_fields(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "a.md").write_text(
        "---\ntitle: Alpha\nupdated: 2026-05-15T10:00:00+00:00\n---\n# Same\nneedle\n",
        encoding="utf-8",
    )
    (source / "b.md").write_text(
        "---\ntitle: Alpha\nupdated: 2026-05-16T10:00:00+00:00\n---\n# Same\nneedle\n",
        encoding="utf-8",
    )
    (source / "c.md").write_text(
        "---\ntitle: Alpha\n---\n# Same\nneedle\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)

    response = search(
        connection,
        SearchRequest(query_text="needle", sort_mode="latest"),
    )

    assert [result.path for result in response.results] == ["b.md", "a.md", "c.md"]
    assert response.results[0].sort_fields["updated_at"] == "2026-05-16T10:00:00+00:00"
    assert response.results[1].sort_fields["updated_at"] == "2026-05-15T10:00:00+00:00"
    assert response.results[2].sort_fields["path"] == "c.md"


def test_retrieval_results_preserve_provenance(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "note.md").write_text(
        "---\ntitle: Provenance\nupdated: 2026-05-16T10:00:00+00:00\ntags: [context]\n---\n# Parent\nignore\n\n## Child\nneedle source text\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    source_root = register_source(connection, source)
    rescan_source(connection, source)

    result = search(connection, SearchRequest(query_text="needle")).results[0]

    assert result.note_id
    assert result.chunk_id
    assert result.evidence_id
    assert result.title == "Provenance"
    assert result.path == "note.md"
    assert result.section_path == ["Parent", "Child"]
    assert result.excerpt == "## Child\nneedle source text"
    assert result.updated_at == "2026-05-16T10:00:00+00:00"
    assert result.file_mtime
    assert result.provenance == {"source_root": source_root, "heading": "Child"}
    assert result.retrieval_mode == "keyword"


def test_repeated_queries_return_identical_ordering(tmp_path):
    connection = _indexed_vault(tmp_path)
    request = SearchRequest(query_text="alpha", limit=10)

    first = search(connection, request)
    second = search(connection, request)

    assert [result.evidence_id for result in first.results] == [
        result.evidence_id for result in second.results
    ]
    assert [asdict(result) for result in first.results] == [
        asdict(result) for result in second.results
    ]


def test_retrieval_is_independent_from_thread_state(tmp_path):
    connection = _indexed_vault(tmp_path)
    connection.execute(
        """
        INSERT INTO threads (thread_id, title, created_at, updated_at, status, summary)
        VALUES (
            'thread-1',
            'Thread Alpha Bias',
            '2026-05-16T10:00:00+00:00',
            '2026-05-16T10:00:00+00:00',
            'active',
            'Prefer some other result'
        )
        """
    )
    connection.commit()

    without_thread = search(connection, SearchRequest(query_text="alpha"))
    with_thread = search(
        connection,
        SearchRequest(query_text="alpha", thread_id="thread-1"),
    )

    assert [asdict(result) for result in with_thread.results] == [
        asdict(result) for result in without_thread.results
    ]


def test_thread_id_does_not_change_retrieval_set_or_ranking(tmp_path):
    connection = _indexed_vault(tmp_path)
    connection.executemany(
        """
        INSERT INTO threads (thread_id, title, created_at, updated_at, status, summary)
        VALUES (?, ?, ?, ?, 'active', ?)
        """,
        [
            (
                "thread-alpha",
                "Alpha Thread",
                "2026-05-16T10:00:00+00:00",
                "2026-05-16T10:00:00+00:00",
                "alpha",
            ),
            (
                "thread-chunk",
                "Chunk Thread",
                "2026-05-16T11:00:00+00:00",
                "2026-05-16T11:00:00+00:00",
                "chunk.md should not be preferred",
            ),
        ],
    )
    connection.commit()
    baseline = search(connection, SearchRequest(query_text="alpha"))
    baseline_ids = [result.evidence_id for result in baseline.results]
    baseline_scores = [result.retrieval_score for result in baseline.results]

    for thread_id in ["thread-alpha", "thread-chunk"]:
        response = search(
            connection,
            SearchRequest(query_text="alpha", thread_id=thread_id),
        )

        assert {result.evidence_id for result in response.results} == set(baseline_ids)
        assert [result.evidence_id for result in response.results] == baseline_ids
        assert [result.retrieval_score for result in response.results] == baseline_scores
        assert [asdict(result) for result in response.results] == [
            asdict(result) for result in baseline.results
        ]


def test_related_notes_use_deterministic_relation_types(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "source.md").write_text(
        "---\ntitle: Source\ntags: [shared]\n---\n# Source\n[[Topic]]\n",
        encoding="utf-8",
    )
    (source / "shared_tag.md").write_text(
        "---\ntitle: Shared Tag\ntags: [shared]\n---\n# Shared\nNo links.\n",
        encoding="utf-8",
    )
    (source / "shared_link.md").write_text(
        "---\ntitle: Shared Link\ntags: [other]\n---\n# Shared\n[[Topic]]\n",
        encoding="utf-8",
    )
    (source / "backlink.md").write_text(
        "---\ntitle: Backlink\ntags: [other]\n---\n# Back\n[[Source]]\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    source_note_id = connection.execute(
        "SELECT note_id FROM notes WHERE path = 'source.md'"
    ).fetchone()["note_id"]

    results = related_notes(connection, source_note_id)

    assert [(result.path, result.relation_types, result.relation_score) for result in results] == [
        ("backlink.md", ["backlink"], 3.0),
        ("shared_link.md", ["shared_wikilink"], 2.0),
        ("shared_tag.md", ["shared_tag"], 1.0),
    ]


def test_related_notes_limit_and_missing_note_are_explicit(tmp_path):
    connection = _indexed_vault(tmp_path)
    note_id = connection.execute(
        "SELECT note_id FROM notes WHERE path = 'tags.md'"
    ).fetchone()["note_id"]

    assert related_notes(connection, note_id, limit=1) == []

    try:
        related_notes(connection, "missing-note")
    except ValueError as exc:
        assert "note does not exist" in str(exc)
    else:
        raise AssertionError("missing note should fail explicitly")


def _indexed_vault(tmp_path):
    source = tmp_path / "vault"
    source.mkdir()
    (source / "title.md").write_text(
        "---\ntitle: Alpha\n---\n# Other\nplain text\n",
        encoding="utf-8",
    )
    (source / "tags.md").write_text(
        "---\ntitle: Tag Match\ntags: [alpha]\n---\n# Other\nplain text\n",
        encoding="utf-8",
    )
    (source / "front.md").write_text(
        "---\ntitle: Front Match\ncategory: alpha\n---\n# Other\nplain text\n",
        encoding="utf-8",
    )
    (source / "chunk.md").write_text(
        "---\ntitle: Chunk Match\n---\n# Other\nalpha appears here\n",
        encoding="utf-8",
    )
    connection = connect_database(tmp_path / "local.db")
    init_database(connection)
    register_source(connection, source)
    rescan_source(connection, source)
    return connection
