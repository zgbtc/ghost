"""Embedded SQLite-backed store for sessions and skill index.

Uses FTS5 for full-text search out of the box. Vector search is added later
when sqlite-vec is available; until then we fall back to FTS-only retrieval,
which is already strong for short-horizon recall.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    created_at  REAL NOT NULL,
    summary     TEXT,
    metadata    TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,        -- user | assistant | tool | system
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL,
    metadata    TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_created ON turns(created_at);

CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
    content,
    session_id UNINDEXED,
    role UNINDEXED,
    content='turns',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN
    INSERT INTO turns_fts(rowid, content, session_id, role)
    VALUES (new.id, new.content, new.session_id, new.role);
END;

CREATE TRIGGER IF NOT EXISTS turns_ad AFTER DELETE ON turns BEGIN
    INSERT INTO turns_fts(turns_fts, rowid, content, session_id, role)
    VALUES ('delete', old.id, old.content, old.session_id, old.role);
END;

CREATE TABLE IF NOT EXISTS skills (
    name        TEXT PRIMARY KEY,
    summary     TEXT NOT NULL,
    triggers    TEXT NOT NULL,        -- JSON array of trigger phrases
    path        TEXT NOT NULL,        -- relative to skills_dir
    success     INTEGER DEFAULT 0,
    failure     INTEGER DEFAULT 0,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

-- Contentless FTS5 over skills, manually synced (rowid maps to skills.rowid)
CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
    name, summary, triggers
);
"""


class MemoryStore:
    """Thin wrapper over SQLite. Single file, no server, no setup."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def conn(self):
        c = self._connect()
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_schema(self) -> None:
        with self.conn() as c:
            c.executescript(SCHEMA)

    # ── Sessions ──────────────────────────────────────────────────────
    def create_session(self, session_id: str, metadata: dict | None = None) -> None:
        with self.conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO sessions(id, created_at, metadata) VALUES (?,?,?)",
                (session_id, time.time(), json.dumps(metadata or {})),
            )

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO turns(session_id, role, content, created_at, metadata) "
                "VALUES (?,?,?,?,?)",
                (session_id, role, content, time.time(), json.dumps(metadata or {})),
            )
            return int(cur.lastrowid)

    def recent_turns(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT role, content, created_at, metadata FROM turns "
                "WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search_turns(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search across all sessions (semantic recall L4)."""
        # FTS5 needs query escaping for special chars
        safe = query.replace('"', '""')
        with self.conn() as c:
            try:
                rows = c.execute(
                    "SELECT t.session_id, t.role, t.content, t.created_at "
                    "FROM turns_fts f JOIN turns t ON t.id = f.rowid "
                    'WHERE turns_fts MATCH ? '
                    "ORDER BY rank LIMIT ?",
                    (f'"{safe}"', limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        return [dict(r) for r in rows]

    # ── Skills index (L1 routing) ─────────────────────────────────────
    def upsert_skill(
        self,
        name: str,
        summary: str,
        triggers: Iterable[str],
        path: str,
    ) -> None:
        now = time.time()
        triggers_list = list(triggers)
        triggers_json = json.dumps(triggers_list)
        # Searchable trigger blob — space-joined for FTS tokenization
        triggers_text = " ".join(triggers_list)
        with self.conn() as c:
            c.execute(
                """
                INSERT INTO skills(name, summary, triggers, path, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET
                    summary=excluded.summary,
                    triggers=excluded.triggers,
                    path=excluded.path,
                    updated_at=excluded.updated_at
                """,
                (name, summary, triggers_json, path, now, now),
            )
            # Manually sync FTS — delete then insert with the skills.rowid
            row = c.execute("SELECT rowid FROM skills WHERE name=?", (name,)).fetchone()
            if row:
                rid = row["rowid"]
                c.execute("DELETE FROM skills_fts WHERE rowid=?", (rid,))
                c.execute(
                    "INSERT INTO skills_fts(rowid, name, summary, triggers) VALUES (?,?,?,?)",
                    (rid, name, summary, triggers_text),
                )

    def find_skills(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        # FTS5 needs each token escaped if used as a phrase. We split into
        # whitespace tokens and build an OR query so partial matches succeed.
        tokens = [t for t in query.replace('"', " ").split() if t]
        if not tokens:
            return []
        match = " OR ".join(f'"{t}"' for t in tokens)
        with self.conn() as c:
            try:
                rows = c.execute(
                    "SELECT s.* FROM skills_fts f JOIN skills s ON s.rowid = f.rowid "
                    "WHERE skills_fts MATCH ? ORDER BY rank LIMIT ?",
                    (match, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        return [dict(r) for r in rows]

    def record_skill_outcome(self, name: str, success: bool) -> None:
        col = "success" if success else "failure"
        with self.conn() as c:
            c.execute(
                f"UPDATE skills SET {col} = {col} + 1, updated_at=? WHERE name=?",
                (time.time(), name),
            )
