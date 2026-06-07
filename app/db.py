"""SQLite 接続とスキーマ初期化（ADR-0001: ローカル完結・端末内保存）。

用語は CONTEXT.md に対応する:
- events    … イベント（取り込んだ1件。元入力・ノート・コミット軸を持つ）
- schedules … 予定（イベント配下の個別の日付項目。種類・締切フラグ・日付を持つ）

日時の確かさ軸（日時確定／日時未定）は schedules.date が NULL かどうかで表す（派生）。
"""

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "calendar.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    source_kind       TEXT NOT NULL CHECK (source_kind IN ('image', 'text')),
    source_text       TEXT,
    source_image      BLOB,
    source_image_mime TEXT,
    note              TEXT NOT NULL DEFAULT '',
    commit_state      TEXT NOT NULL DEFAULT 'floating'
                      CHECK (commit_state IN ('floating', 'committed')),
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    kind          TEXT,
    is_deadline   INTEGER NOT NULL DEFAULT 0,
    date          TEXT,
    time          TEXT,
    raw_date_text TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schedules_event_id ON schedules (event_id);
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules (date);
"""


def connect() -> sqlite3.Connection:
    """端末内の SQLite に接続する。data/ が無ければ作る。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """テーブルが無ければ作成する。アプリ起動時に呼ぶ。"""
    with connect() as conn:
        conn.executescript(_SCHEMA)
