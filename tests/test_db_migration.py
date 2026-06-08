"""コミット軸のイベント単位→予定単位 移行（_migrate）の振る舞いテスト。"""

import sqlite3

from app.db import _migrate

# commit_state がイベント側にあった旧スキーマ（schedules には無い）。
_OLD_SCHEMA = """
CREATE TABLE events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    commit_state TEXT NOT NULL DEFAULT 'floating'
                 CHECK (commit_state IN ('floating', 'committed')),
    created_at   TEXT NOT NULL
);
CREATE TABLE schedules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _old_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_OLD_SCHEMA)
    return conn


def test_migrate_carries_event_state_to_schedules() -> None:
    conn = _old_db()
    conn.execute(
        "INSERT INTO events (id, title, commit_state, created_at) "
        "VALUES (1, 'committed-ev', 'committed', 'now')"
    )
    conn.execute(
        "INSERT INTO events (id, title, commit_state, created_at) "
        "VALUES (2, 'floating-ev', 'floating', 'now')"
    )
    conn.executemany(
        "INSERT INTO schedules (event_id, title, created_at) VALUES (?, ?, 'now')",
        [(1, "a"), (1, "b"), (2, "c")],
    )
    conn.commit()

    _migrate(conn)

    states = dict(
        conn.execute(
            "SELECT event_id, commit_state FROM schedules ORDER BY event_id"
        ).fetchall()
    )
    # 親イベントの確定状態を各予定が引き継ぐ。
    assert states[1] == "committed"
    assert states[2] == "floating"


def test_migrate_drops_event_commit_state_column() -> None:
    conn = _old_db()
    _migrate(conn)
    event_cols = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
    assert "commit_state" not in event_cols


def test_migrate_tolerates_orphan_schedule() -> None:
    # 親イベントが消えた孤児予定があっても落ちず、既定の floating になる。
    conn = _old_db()
    conn.execute(
        "INSERT INTO schedules (event_id, title, created_at) VALUES (999, 'x', 'now')"
    )
    conn.commit()
    _migrate(conn)
    state = conn.execute("SELECT commit_state FROM schedules").fetchone()[0]
    assert state == "floating"


def test_migrate_is_idempotent() -> None:
    conn = _old_db()
    _migrate(conn)
    _migrate(conn)  # 2回目は何もしない（例外なく通る）
    sched_cols = {row["name"] for row in conn.execute("PRAGMA table_info(schedules)")}
    assert "commit_state" in sched_cols
