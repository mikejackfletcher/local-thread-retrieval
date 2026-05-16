from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from .schema import (
    BacklogEvidenceLinkRecord,
    BacklogHistoryRecord,
    BacklogItemRecord,
)


NAMESPACE = uuid.UUID("b82776f2-5d3d-43d1-b3f2-794f33ee7c9c")
BACKLOG_STATUSES = {"proposed", "triaged", "ready", "done", "dropped"}
PRIORITIES = {"low", "medium", "high"}
ACTION_TYPES = {"review", "write-note", "follow-up", "research", "externalise"}
LINK_TYPES = {"supporting", "primary"}


def create_backlog_item(
    connection: sqlite3.Connection,
    *,
    title: str,
    description: str,
    evidence_ids: list[str],
    thread_id: str | None = None,
    priority: str = "medium",
    action_type: str = "review",
    confidence: float = 0.0,
    created_at: str | None = None,
) -> BacklogItemRecord:
    if not evidence_ids:
        raise ValueError("backlog item requires at least one evidence record")
    if priority not in PRIORITIES:
        raise ValueError("priority must be low, medium, or high")
    if action_type not in ACTION_TYPES:
        raise ValueError("action_type is not supported")
    if thread_id is not None:
        _require_thread(connection, thread_id)
    for evidence_id in evidence_ids:
        _require_evidence(connection, evidence_id)

    timestamp = created_at or _now()
    backlog_id = _stable_id("backlog", title, description, timestamp)
    with connection:
        connection.execute(
            """
            INSERT INTO backlog_items (
                backlog_id, thread_id, title, description, status, priority,
                action_type, confidence, requires_confirmation, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'proposed', ?, ?, ?, 1, ?, ?)
            """,
            (
                backlog_id,
                thread_id,
                title,
                description,
                priority,
                action_type,
                float(confidence),
                timestamp,
                timestamp,
            ),
        )
        _insert_history(connection, backlog_id, None, "proposed", timestamp)
        for index, evidence_id in enumerate(evidence_ids):
            link_type = "primary" if index == 0 else "supporting"
            _insert_backlog_evidence_link(
                connection,
                backlog_id,
                evidence_id,
                link_type,
            )
    return get_backlog_item(connection, backlog_id)


def transition_backlog_status(
    connection: sqlite3.Connection,
    backlog_id: str,
    status: str,
    *,
    changed_at: str | None = None,
) -> BacklogItemRecord:
    if status not in BACKLOG_STATUSES:
        raise ValueError("status must be proposed, triaged, ready, done, or dropped")
    item = get_backlog_item(connection, backlog_id)
    if item is None:
        raise ValueError(f"backlog item does not exist: {backlog_id}")
    timestamp = changed_at or _now()
    with connection:
        connection.execute(
            """
            UPDATE backlog_items
            SET status = ?, updated_at = ?
            WHERE backlog_id = ?
            """,
            (status, timestamp, backlog_id),
        )
        _insert_history(connection, backlog_id, item.status, status, timestamp)
    return get_backlog_item(connection, backlog_id)


def get_backlog_item(
    connection: sqlite3.Connection,
    backlog_id: str,
) -> BacklogItemRecord | None:
    row = connection.execute(
        "SELECT * FROM backlog_items WHERE backlog_id = ?",
        (backlog_id,),
    ).fetchone()
    if row is None:
        return None
    return _item_from_row(row)


def list_backlog_evidence_links(
    connection: sqlite3.Connection,
    backlog_id: str,
) -> list[BacklogEvidenceLinkRecord]:
    if get_backlog_item(connection, backlog_id) is None:
        raise ValueError(f"backlog item does not exist: {backlog_id}")
    rows = connection.execute(
        """
        SELECT * FROM backlog_evidence_links
        WHERE backlog_id = ?
        ORDER BY link_type, link_id
        """,
        (backlog_id,),
    ).fetchall()
    return [_link_from_row(row) for row in rows]


def list_backlog_history(
    connection: sqlite3.Connection,
    backlog_id: str,
) -> list[BacklogHistoryRecord]:
    if get_backlog_item(connection, backlog_id) is None:
        raise ValueError(f"backlog item does not exist: {backlog_id}")
    rows = connection.execute(
        """
        SELECT * FROM backlog_history
        WHERE backlog_id = ?
        ORDER BY changed_at, history_id
        """,
        (backlog_id,),
    ).fetchall()
    return [_history_from_row(row) for row in rows]


def _insert_backlog_evidence_link(
    connection: sqlite3.Connection,
    backlog_id: str,
    evidence_id: str,
    link_type: str,
) -> None:
    if link_type not in LINK_TYPES:
        raise ValueError("link_type must be supporting or primary")
    connection.execute(
        """
        INSERT INTO backlog_evidence_links (
            link_id, backlog_id, evidence_id, link_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (_stable_id("backlog-link", backlog_id, evidence_id, link_type), backlog_id, evidence_id, link_type),
    )


def _insert_history(
    connection: sqlite3.Connection,
    backlog_id: str,
    from_status: str | None,
    to_status: str,
    changed_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO backlog_history (
            history_id, backlog_id, from_status, to_status, changed_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            _stable_id("backlog-history", backlog_id, str(from_status), to_status, changed_at),
            backlog_id,
            from_status,
            to_status,
            changed_at,
        ),
    )


def _require_evidence(connection: sqlite3.Connection, evidence_id: str) -> None:
    row = connection.execute(
        "SELECT 1 FROM evidence WHERE evidence_id = ?",
        (evidence_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"evidence does not exist: {evidence_id}")


def _require_thread(connection: sqlite3.Connection, thread_id: str) -> None:
    row = connection.execute(
        "SELECT 1 FROM threads WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"thread does not exist: {thread_id}")


def _item_from_row(row: sqlite3.Row) -> BacklogItemRecord:
    return BacklogItemRecord(
        backlog_id=row["backlog_id"],
        thread_id=row["thread_id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        priority=row["priority"],
        action_type=row["action_type"],
        confidence=row["confidence"],
        requires_confirmation=bool(row["requires_confirmation"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _link_from_row(row: sqlite3.Row) -> BacklogEvidenceLinkRecord:
    return BacklogEvidenceLinkRecord(
        link_id=row["link_id"],
        backlog_id=row["backlog_id"],
        evidence_id=row["evidence_id"],
        link_type=row["link_type"],
    )


def _history_from_row(row: sqlite3.Row) -> BacklogHistoryRecord:
    return BacklogHistoryRecord(
        history_id=row["history_id"],
        backlog_id=row["backlog_id"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        changed_at=row["changed_at"],
    )


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "\x1f".join(parts)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
