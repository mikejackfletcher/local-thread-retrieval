from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import connect_database, init_database
from .ingest import register_source, rescan_source


SOURCE_DERIVED_TABLES = ("notes", "note_metadata", "chunks", "links")


@dataclass(frozen=True)
class InvariantViolation:
    name: str
    detail: str


def deterministic_rebuild_snapshot(
    database_path: str | Path,
    source_root: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    connection = connect_database(database_path)
    init_database(connection)
    register_source(connection, source_root)
    rescan_source(connection, source_root)
    return source_derived_snapshot(connection)


def source_derived_snapshot(
    connection: sqlite3.Connection,
) -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {}
    snapshot["notes"] = [
        _without(row, "file_mtime")
        for row in connection.execute(
            """
            SELECT * FROM notes
            ORDER BY source_root, path
            """
        ).fetchall()
    ]
    snapshot["note_metadata"] = [
        dict(row)
        for row in connection.execute(
            """
            SELECT * FROM note_metadata
            ORDER BY note_id, key
            """
        ).fetchall()
    ]
    snapshot["chunks"] = [
        dict(row)
        for row in connection.execute(
            """
            SELECT * FROM chunks
            ORDER BY note_id, chunk_index
            """
        ).fetchall()
    ]
    snapshot["links"] = [
        dict(row)
        for row in connection.execute(
            """
            SELECT * FROM links
            ORDER BY note_id, target, link_type
            """
        ).fetchall()
    ]
    return snapshot


def validate_invariants(connection: sqlite3.Connection) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    violations.extend(_duplicate_violations(connection))
    violations.extend(_evidence_traceability_violations(connection))
    violations.extend(_thread_summary_boundary_violations(connection))
    violations.extend(_backlog_boundary_violations(connection))
    return violations


def assert_invariants(connection: sqlite3.Connection) -> None:
    violations = validate_invariants(connection)
    if violations:
        details = "; ".join(
            f"{violation.name}: {violation.detail}" for violation in violations
        )
        raise AssertionError(details)


def row_counts(
    connection: sqlite3.Connection,
    tables: tuple[str, ...],
) -> dict[str, int]:
    return {
        table: connection.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        ).fetchone()["count"]
        for table in tables
    }


def _duplicate_violations(
    connection: sqlite3.Connection,
) -> list[InvariantViolation]:
    checks = [
        (
            "duplicate_note_identity",
            """
            SELECT source_root || ':' || path AS identity, COUNT(*) AS count
            FROM notes
            GROUP BY source_root, path
            HAVING COUNT(*) > 1
            """,
        ),
        (
            "duplicate_chunk_identity",
            """
            SELECT note_id || ':' || chunk_index AS identity, COUNT(*) AS count
            FROM chunks
            GROUP BY note_id, chunk_index
            HAVING COUNT(*) > 1
            """,
        ),
        (
            "duplicate_link_identity",
            """
            SELECT note_id || ':' || target || ':' || link_type AS identity,
                   COUNT(*) AS count
            FROM links
            GROUP BY note_id, target, link_type
            HAVING COUNT(*) > 1
            """,
        ),
    ]
    violations: list[InvariantViolation] = []
    for name, sql in checks:
        for row in connection.execute(sql).fetchall():
            violations.append(InvariantViolation(name, row["identity"]))
    return violations


def _evidence_traceability_violations(
    connection: sqlite3.Connection,
) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    rows = connection.execute(
        """
        SELECT
            evidence.evidence_id,
            evidence.note_id AS evidence_note_id,
            evidence.path AS evidence_path,
            evidence.title AS evidence_title,
            evidence.source_root AS evidence_source_root,
            evidence.section_path AS evidence_section_path,
            evidence.heading AS evidence_heading,
            evidence.excerpt,
            evidence.excerpt_char_start,
            evidence.excerpt_char_end,
            evidence.updated_at AS evidence_updated_at,
            evidence.file_mtime AS evidence_file_mtime,
            chunks.note_id AS chunk_note_id,
            chunks.section_path AS chunk_section_path,
            chunks.heading AS chunk_heading,
            chunks.text AS chunk_text,
            notes.path AS note_path,
            notes.title AS note_title,
            notes.source_root AS note_source_root,
            notes.updated_at AS note_updated_at,
            notes.file_mtime AS note_file_mtime
        FROM evidence
        LEFT JOIN chunks ON chunks.chunk_id = evidence.chunk_id
        LEFT JOIN notes ON notes.note_id = evidence.note_id
        """
    ).fetchall()
    for row in rows:
        evidence_id = row["evidence_id"]
        if row["chunk_note_id"] is None or row["note_path"] is None:
            violations.append(
                InvariantViolation("evidence_missing_source", evidence_id)
            )
            continue
        expected_excerpt = row["chunk_text"][
            row["excerpt_char_start"] : row["excerpt_char_end"]
        ]
        if row["excerpt"] != expected_excerpt:
            violations.append(
                InvariantViolation("evidence_excerpt_not_contiguous", evidence_id)
            )
        if len(row["excerpt"]) > 500:
            violations.append(
                InvariantViolation("evidence_excerpt_too_long", evidence_id)
            )
        provenance_pairs = [
            ("note_id", row["evidence_note_id"], row["chunk_note_id"]),
            ("path", row["evidence_path"], row["note_path"]),
            ("title", row["evidence_title"], row["note_title"]),
            ("source_root", row["evidence_source_root"], row["note_source_root"]),
            ("section_path", row["evidence_section_path"], row["chunk_section_path"]),
            ("heading", row["evidence_heading"], row["chunk_heading"]),
            ("updated_at", row["evidence_updated_at"], row["note_updated_at"]),
            ("file_mtime", row["evidence_file_mtime"], row["note_file_mtime"]),
        ]
        for field, actual, expected in provenance_pairs:
            if actual != expected:
                violations.append(
                    InvariantViolation(
                        "evidence_provenance_mismatch",
                        f"{evidence_id}:{field}",
                    )
                )
    return violations


def _thread_summary_boundary_violations(
    connection: sqlite3.Connection,
) -> list[InvariantViolation]:
    rows = connection.execute(
        """
        SELECT thread_synthesis.synthesis_id
        FROM thread_synthesis
        JOIN evidence ON evidence.evidence_id = thread_synthesis.synthesis_id
        """
    ).fetchall()
    return [
        InvariantViolation("thread_summary_stored_as_evidence", row["synthesis_id"])
        for row in rows
    ]


def _backlog_boundary_violations(
    connection: sqlite3.Connection,
) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    missing_links = connection.execute(
        """
        SELECT backlog_items.backlog_id
        FROM backlog_items
        LEFT JOIN backlog_evidence_links
          ON backlog_evidence_links.backlog_id = backlog_items.backlog_id
        GROUP BY backlog_items.backlog_id
        HAVING COUNT(backlog_evidence_links.link_id) = 0
        """
    ).fetchall()
    for row in missing_links:
        violations.append(
            InvariantViolation("backlog_without_evidence", row["backlog_id"])
        )

    id_collisions = connection.execute(
        """
        SELECT backlog_items.backlog_id, 'note' AS target
        FROM backlog_items
        JOIN notes ON notes.note_id = backlog_items.backlog_id
        UNION ALL
        SELECT backlog_items.backlog_id, 'evidence' AS target
        FROM backlog_items
        JOIN evidence ON evidence.evidence_id = backlog_items.backlog_id
        """
    ).fetchall()
    for row in id_collisions:
        violations.append(
            InvariantViolation(
                "backlog_treated_as_source_truth",
                f"{row['backlog_id']}:{row['target']}",
            )
        )
    return violations


def _without(row: sqlite3.Row, *keys: str) -> dict[str, Any]:
    result = dict(row)
    for key in keys:
        result.pop(key, None)
    return result
