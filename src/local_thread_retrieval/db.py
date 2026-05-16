from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_roots (
    source_root TEXT PRIMARY KEY,
    registered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    source_root TEXT NOT NULL,
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    front_matter TEXT NOT NULL,
    tags TEXT NOT NULL,
    wikilinks TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    file_mtime TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    parse_status TEXT NOT NULL CHECK (parse_status IN ('ok', 'error')),
    UNIQUE (source_root, path),
    FOREIGN KEY (source_root) REFERENCES source_roots(source_root) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS note_metadata (
    metadata_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE (note_id, key),
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    heading TEXT,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    retrieval_text TEXT NOT NULL,
    embedding_vector TEXT,
    UNIQUE (note_id, chunk_index),
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS links (
    link_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    target TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'wikilink',
    UNIQUE (note_id, target, link_type),
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    chunk_id TEXT,
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    section_path TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    updated_at TEXT,
    retrieval_score REAL NOT NULL,
    retrieval_mode TEXT NOT NULL CHECK (retrieval_mode IN ('keyword', 'hybrid', 'semantic')),
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'archived')),
    summary TEXT
);

CREATE TABLE IF NOT EXISTS thread_messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'system', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pinned_evidence (
    pin_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    pinned_at TEXT NOT NULL,
    pin_reason TEXT,
    UNIQUE (thread_id, evidence_id),
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS thread_synthesis (
    synthesis_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    content TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backlog_items (
    backlog_id TEXT PRIMARY KEY,
    thread_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed', 'triaged', 'ready', 'done', 'dropped')),
    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    action_type TEXT NOT NULL CHECK (action_type IN ('review', 'write-note', 'follow-up', 'research', 'externalise')),
    confidence REAL NOT NULL,
    requires_confirmation INTEGER NOT NULL CHECK (requires_confirmation IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS backlog_evidence_links (
    link_id TEXT PRIMARY KEY,
    backlog_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK (link_type IN ('supporting', 'primary')),
    UNIQUE (backlog_id, evidence_id, link_type),
    FOREIGN KEY (backlog_id) REFERENCES backlog_items(backlog_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backlog_history (
    history_id TEXT PRIMARY KEY,
    backlog_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (backlog_id) REFERENCES backlog_items(backlog_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.commit()
