from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .parser import parse_markdown


NAMESPACE = uuid.UUID("5f769793-9b17-45d8-9351-e86d4367d68a")


def register_source(connection: sqlite3.Connection, source_root: str | Path) -> str:
    root = _normalise_root(source_root)
    connection.execute(
        "INSERT OR IGNORE INTO source_roots (source_root) VALUES (?)",
        (root,),
    )
    connection.commit()
    return root


def list_sources(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT source_root FROM source_roots ORDER BY source_root"
    ).fetchall()
    return [row["source_root"] for row in rows]


def rescan_source(connection: sqlite3.Connection, source_root: str | Path) -> None:
    root = _normalise_root(source_root)
    registered = connection.execute(
        "SELECT 1 FROM source_roots WHERE source_root = ?",
        (root,),
    ).fetchone()
    if not registered:
        raise ValueError(f"source root is not registered: {root}")

    root_path = Path(root)
    if not root_path.exists():
        return

    seen_paths: set[str] = set()

    with connection:
        for markdown_path in sorted(root_path.rglob("*.md")):
            if not markdown_path.is_file():
                continue
            relative_path = markdown_path.relative_to(root_path).as_posix()
            seen_paths.add(relative_path)
            _ingest_markdown_file(connection, root, relative_path, markdown_path)

        stored_paths = connection.execute(
            "SELECT path FROM notes WHERE source_root = ?",
            (root,),
        ).fetchall()
        for row in stored_paths:
            if row["path"] not in seen_paths:
                connection.execute(
                    "DELETE FROM notes WHERE source_root = ? AND path = ?",
                    (root, row["path"]),
                )


def _ingest_markdown_file(
    connection: sqlite3.Connection,
    source_root: str,
    relative_path: str,
    markdown_path: Path,
) -> None:
    raw = markdown_path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    existing = connection.execute(
        "SELECT note_id, file_hash FROM notes WHERE source_root = ? AND path = ?",
        (source_root, relative_path),
    ).fetchone()
    if existing and existing["file_hash"] == file_hash:
        return

    text = raw.decode("utf-8")
    parsed = parse_markdown(Path(relative_path), text)
    note_id = _stable_id("note", source_root, relative_path)
    stat = markdown_path.stat()

    connection.execute(
        """
        INSERT INTO notes (
            note_id, source_root, path, title, front_matter, tags, wikilinks,
            created_at, updated_at, file_mtime, file_hash, parse_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_root, path) DO UPDATE SET
            title = excluded.title,
            front_matter = excluded.front_matter,
            tags = excluded.tags,
            wikilinks = excluded.wikilinks,
            created_at = excluded.created_at,
            updated_at = excluded.updated_at,
            file_mtime = excluded.file_mtime,
            file_hash = excluded.file_hash,
            parse_status = excluded.parse_status
        """,
        (
            note_id,
            source_root,
            relative_path,
            parsed.title,
            _json(parsed.front_matter),
            _json(parsed.tags),
            _json(parsed.wikilinks),
            _iso(parsed.created_at),
            _iso(parsed.updated_at),
            _iso(datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)),
            file_hash,
            parsed.parse_status,
        ),
    )

    connection.execute("DELETE FROM chunks WHERE note_id = ?", (note_id,))
    connection.execute("DELETE FROM links WHERE note_id = ?", (note_id,))
    connection.execute("DELETE FROM note_metadata WHERE note_id = ?", (note_id,))

    for chunk in parsed.chunks:
        connection.execute(
            """
            INSERT INTO chunks (
                chunk_id, note_id, section_path, heading, text, char_start,
                char_end, chunk_index, retrieval_text, embedding_vector
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                _stable_id("chunk", note_id, str(chunk.chunk_index)),
                note_id,
                _json(chunk.section_path),
                chunk.heading,
                chunk.text,
                chunk.char_start,
                chunk.char_end,
                chunk.chunk_index,
                chunk.retrieval_text,
            ),
        )

    for link in parsed.links:
        connection.execute(
            """
            INSERT OR IGNORE INTO links (link_id, note_id, target, link_type)
            VALUES (?, ?, ?, ?)
            """,
            (
                _stable_id("link", note_id, link.target, link.link_type),
                note_id,
                link.target,
                link.link_type,
            ),
        )

    for key, value in sorted(parsed.front_matter.items()):
        connection.execute(
            """
            INSERT OR REPLACE INTO note_metadata (metadata_id, note_id, key, value)
            VALUES (?, ?, ?, ?)
            """,
            (_stable_id("metadata", note_id, str(key)), note_id, str(key), _json(value)),
        )


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "\x1f".join(parts)))


def _normalise_root(source_root: str | Path) -> str:
    return str(Path(source_root).expanduser().resolve())


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
