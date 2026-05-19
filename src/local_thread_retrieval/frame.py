from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence

from .evidence import get_evidence
from .schema import EvidenceRecord, SearchResult
from .threads import get_thread, list_pinned_evidence, list_thread_messages


def assemble_chatgpt_frame(
    connection: sqlite3.Connection,
    *,
    retrieval_results: Sequence[SearchResult] = (),
    evidence_ids: Sequence[str] = (),
    thread_id: str | None = None,
) -> str:
    lines: list[str] = [
        "CHATGPT CONTEXT FRAME",
        "",
        "BOUNDARIES",
        "- This frame is assembled locally for manual copy/paste.",
        "- Source excerpts are evidence only when listed in the evidence section.",
        "- Thread summaries are labelled summaries, not evidence.",
        "- Do not treat thread state or backlog items as source notes.",
        "",
    ]

    if thread_id is not None:
        lines.extend(_thread_context(connection, thread_id))
        lines.append("")

    lines.extend(_retrieval_results(retrieval_results))
    lines.append("")
    lines.extend(_evidence_records(connection, evidence_ids))

    return "\n".join(lines).rstrip() + "\n"


def _thread_context(
    connection: sqlite3.Connection,
    thread_id: str,
) -> list[str]:
    thread = get_thread(connection, thread_id)
    if thread is None:
        raise ValueError(f"thread does not exist: {thread_id}")

    lines = [
        "THREAD CONTEXT",
        f"Thread ID: {thread.thread_id}",
        f"Title: {thread.title}",
        f"Status: {thread.status}",
        f"Created: {thread.created_at}",
        f"Updated: {thread.updated_at}",
        "",
        "THREAD MESSAGES",
    ]
    messages = list_thread_messages(connection, thread_id)
    if messages:
        for message in messages:
            lines.extend(
                [
                    f"- Message ID: {message.message_id}",
                    f"  Role: {message.role}",
                    f"  Created: {message.created_at}",
                    "  Content:",
                    _indent(message.content, "    "),
                ]
            )
    else:
        lines.append("- None")

    summaries = _thread_summaries(connection, thread_id)
    lines.extend(["", "THREAD SUMMARIES (NOT EVIDENCE)"])
    if summaries:
        for summary in summaries:
            lines.extend(
                [
                    f"- Summary ID: {summary['synthesis_id']}",
                    f"  Created: {summary['created_at']}",
                    f"  Referenced evidence IDs: {summary['evidence_ids']}",
                    "  Summary content:",
                    _indent(summary["content"], "    "),
                ]
            )
    else:
        lines.append("- None")

    pins = list_pinned_evidence(connection, thread_id)
    lines.extend(["", "PINNED EVIDENCE REFERENCES"])
    if pins:
        for pin in pins:
            lines.extend(
                [
                    f"- Pin ID: {pin.pin_id}",
                    f"  Evidence ID: {pin.evidence_id}",
                    f"  Pinned at: {pin.pinned_at}",
                    f"  Reason: {pin.pin_reason or ''}",
                ]
            )
    else:
        lines.append("- None")
    return lines


def _retrieval_results(
    retrieval_results: Sequence[SearchResult],
) -> list[str]:
    lines = ["RETRIEVAL RESULTS"]
    if not retrieval_results:
        lines.append("- None")
        return lines

    for index, result in enumerate(retrieval_results, start=1):
        lines.extend(
            [
                f"[Retrieval Result {index}]",
                f"Evidence ID: {result.evidence_id}",
                f"Note ID: {result.note_id}",
                f"Chunk ID: {result.chunk_id}",
                f"Title: {result.title}",
                f"Path: {result.path}",
                f"Section path: {json.dumps(result.section_path, separators=(',', ':'))}",
                f"Updated at: {result.updated_at or ''}",
                f"File mtime: {result.file_mtime}",
                f"Retrieval score: {result.retrieval_score}",
                f"Retrieval mode: {result.retrieval_mode}",
                f"Provenance source_root: {result.provenance['source_root']}",
                f"Provenance heading: {result.provenance['heading'] or ''}",
                "Excerpt:",
                _indent(result.excerpt, "  "),
                "",
            ]
        )
    if lines[-1] == "":
        lines.pop()
    return lines


def _evidence_records(
    connection: sqlite3.Connection,
    evidence_ids: Sequence[str],
) -> list[str]:
    lines = ["EVIDENCE RECORDS"]
    if not evidence_ids:
        lines.append("- None")
        return lines

    for evidence_id in evidence_ids:
        evidence = get_evidence(connection, evidence_id)
        if evidence is None:
            raise ValueError(f"evidence does not exist: {evidence_id}")
        lines.extend(_evidence_record(evidence))
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def _evidence_record(evidence: EvidenceRecord) -> list[str]:
    excerpt = evidence.excerpt
    if len(excerpt) > 500:
        raise ValueError(f"evidence excerpt exceeds 500 characters: {evidence.evidence_id}")
    return [
        f"[Evidence {evidence.evidence_id}]",
        f"Note ID: {evidence.note_id}",
        f"Chunk ID: {evidence.chunk_id}",
        f"Title: {evidence.title}",
        f"Path: {evidence.path}",
        f"Source root: {evidence.source_root}",
        f"Section path: {json.dumps(evidence.section_path, separators=(',', ':'))}",
        f"Heading: {evidence.heading or ''}",
        f"Updated at: {evidence.updated_at or ''}",
        f"File mtime: {evidence.file_mtime}",
        f"Retrieval score: {evidence.retrieval_score}",
        f"Retrieval mode: {evidence.retrieval_mode}",
        f"Excerpt character range: {evidence.excerpt_char_start}:{evidence.excerpt_char_end}",
        "Excerpt:",
        _indent(excerpt, "  "),
    ]


def _thread_summaries(
    connection: sqlite3.Connection,
    thread_id: str,
) -> list[dict[str, str]]:
    rows = connection.execute(
        """
        SELECT synthesis_id, content, evidence_ids, created_at
        FROM thread_synthesis
        WHERE thread_id = ?
        ORDER BY created_at, synthesis_id
        """,
        (thread_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _indent(text: str, prefix: str) -> str:
    if text == "":
        return prefix
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
