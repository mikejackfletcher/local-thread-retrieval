from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from .schema import (
    PinnedEvidenceRecord,
    ThreadMessageRecord,
    ThreadRecord,
    ThreadSummaryRecord,
)


NAMESPACE = uuid.UUID("aab73335-a397-4f74-9ebd-d0557c229ee8")
THREAD_STATUSES = {"active", "paused", "archived"}
MESSAGE_ROLES = {"user", "system", "assistant"}


def create_thread(
    connection: sqlite3.Connection,
    title: str,
    *,
    status: str = "active",
    created_at: str | None = None,
) -> ThreadRecord:
    if status not in THREAD_STATUSES:
        raise ValueError("thread status must be active, paused, or archived")
    timestamp = created_at or _now()
    thread_id = _stable_id("thread", title, timestamp)
    connection.execute(
        """
        INSERT INTO threads (thread_id, title, created_at, updated_at, status, summary)
        VALUES (?, ?, ?, ?, ?, NULL)
        """,
        (thread_id, title, timestamp, timestamp, status),
    )
    connection.commit()
    return _thread_from_row(
        connection.execute(
            "SELECT * FROM threads WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
    )


def add_thread_message(
    connection: sqlite3.Connection,
    thread_id: str,
    role: str,
    content: str,
    *,
    created_at: str | None = None,
) -> ThreadMessageRecord:
    if role not in MESSAGE_ROLES:
        raise ValueError("message role must be user, system, or assistant")
    _require_thread(connection, thread_id)
    timestamp = created_at or _now()
    message_id = _stable_id("message", thread_id, role, content, timestamp)
    with connection:
        connection.execute(
            """
            INSERT INTO thread_messages (message_id, thread_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, thread_id, role, content, timestamp),
        )
        connection.execute(
            "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
            (timestamp, thread_id),
        )
    return _message_from_row(
        connection.execute(
            "SELECT * FROM thread_messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    )


def pin_evidence(
    connection: sqlite3.Connection,
    thread_id: str,
    evidence_id: str,
    *,
    pin_reason: str | None = None,
    pinned_at: str | None = None,
) -> PinnedEvidenceRecord:
    _require_thread(connection, thread_id)
    _require_evidence(connection, evidence_id)
    timestamp = pinned_at or _now()
    pin_id = _stable_id("pin", thread_id, evidence_id)
    with connection:
        connection.execute(
            """
            INSERT INTO pinned_evidence (
                pin_id, thread_id, evidence_id, pinned_at, pin_reason
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(thread_id, evidence_id) DO UPDATE SET
                pin_reason = excluded.pin_reason
            """,
            (pin_id, thread_id, evidence_id, timestamp, pin_reason),
        )
        connection.execute(
            "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
            (timestamp, thread_id),
        )
    return _pin_from_row(
        connection.execute(
            "SELECT * FROM pinned_evidence WHERE pin_id = ?",
            (pin_id,),
        ).fetchone()
    )


def list_pinned_evidence(
    connection: sqlite3.Connection,
    thread_id: str,
) -> list[PinnedEvidenceRecord]:
    _require_thread(connection, thread_id)
    rows = connection.execute(
        """
        SELECT * FROM pinned_evidence
        WHERE thread_id = ?
        ORDER BY pinned_at, pin_id
        """,
        (thread_id,),
    ).fetchall()
    return [_pin_from_row(row) for row in rows]


def store_thread_summary(
    connection: sqlite3.Connection,
    thread_id: str,
    content: str,
    *,
    evidence_ids: list[str] | None = None,
    created_at: str | None = None,
) -> ThreadSummaryRecord:
    _require_thread(connection, thread_id)
    evidence_ids = evidence_ids or []
    for evidence_id in evidence_ids:
        _require_pinned_evidence(connection, thread_id, evidence_id)
    timestamp = created_at or _now()
    synthesis_id = _stable_id("summary", thread_id, content, timestamp)
    with connection:
        connection.execute(
            """
            INSERT INTO thread_synthesis (
                synthesis_id, thread_id, content, evidence_ids, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                synthesis_id,
                thread_id,
                content,
                json.dumps(evidence_ids, sort_keys=True, separators=(",", ":")),
                timestamp,
            ),
        )
        connection.execute(
            "UPDATE threads SET summary = ?, updated_at = ? WHERE thread_id = ?",
            (content, timestamp, thread_id),
        )
    return _summary_from_row(
        connection.execute(
            "SELECT * FROM thread_synthesis WHERE synthesis_id = ?",
            (synthesis_id,),
        ).fetchone()
    )


def get_thread(connection: sqlite3.Connection, thread_id: str) -> ThreadRecord | None:
    row = connection.execute(
        "SELECT * FROM threads WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    if row is None:
        return None
    return _thread_from_row(row)


def list_thread_messages(
    connection: sqlite3.Connection,
    thread_id: str,
) -> list[ThreadMessageRecord]:
    _require_thread(connection, thread_id)
    rows = connection.execute(
        """
        SELECT * FROM thread_messages
        WHERE thread_id = ?
        ORDER BY created_at, message_id
        """,
        (thread_id,),
    ).fetchall()
    return [_message_from_row(row) for row in rows]


def _require_thread(connection: sqlite3.Connection, thread_id: str) -> None:
    if get_thread(connection, thread_id) is None:
        raise ValueError(f"thread does not exist: {thread_id}")


def _require_evidence(connection: sqlite3.Connection, evidence_id: str) -> None:
    row = connection.execute(
        "SELECT 1 FROM evidence WHERE evidence_id = ?",
        (evidence_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"evidence does not exist: {evidence_id}")


def _require_pinned_evidence(
    connection: sqlite3.Connection,
    thread_id: str,
    evidence_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1 FROM pinned_evidence
        WHERE thread_id = ? AND evidence_id = ?
        """,
        (thread_id, evidence_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"evidence is not pinned to thread: {evidence_id}")


def _thread_from_row(row: sqlite3.Row) -> ThreadRecord:
    return ThreadRecord(
        thread_id=row["thread_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        status=row["status"],
        summary=row["summary"],
    )


def _message_from_row(row: sqlite3.Row) -> ThreadMessageRecord:
    return ThreadMessageRecord(
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
    )


def _pin_from_row(row: sqlite3.Row) -> PinnedEvidenceRecord:
    return PinnedEvidenceRecord(
        pin_id=row["pin_id"],
        thread_id=row["thread_id"],
        evidence_id=row["evidence_id"],
        pinned_at=row["pinned_at"],
        pin_reason=row["pin_reason"],
    )


def _summary_from_row(row: sqlite3.Row) -> ThreadSummaryRecord:
    return ThreadSummaryRecord(
        synthesis_id=row["synthesis_id"],
        thread_id=row["thread_id"],
        content=row["content"],
        evidence_ids=json.loads(row["evidence_ids"]),
        created_at=row["created_at"],
    )


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "\x1f".join(parts)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
