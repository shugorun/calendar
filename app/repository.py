"""events / schedules の保存・取得（ADR-0004: 識別は内部ID、名前はユーザー所有）。"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.extraction.adapter import ExtractionInput, ExtractionResult


@dataclass
class ScheduleRow:
    id: int
    title: str
    kind: str | None
    is_deadline: bool
    date: str | None
    time: str | None
    raw_date_text: str | None


@dataclass
class EventRow:
    id: int
    title: str
    source_kind: str
    note: str
    commit_state: str
    schedules: list[ScheduleRow]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_event(
    conn: sqlite3.Connection, source: ExtractionInput, result: ExtractionResult
) -> int:
    """イベント1件とその予定をまとめて保存し、イベントIDを返す。"""
    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO events "
        "(title, source_kind, source_text, source_image, "
        "source_image_mime, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            result.event_title,
            source.kind,
            source.text,
            source.image,
            source.image_mime,
            now,
        ),
    )
    event_id = cur.lastrowid
    if event_id is None:
        raise RuntimeError("events への INSERT で id が取得できなかった")
    for sched in result.schedules:
        conn.execute(
            "INSERT INTO schedules "
            "(event_id, title, kind, is_deadline, date, time, "
            "raw_date_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                sched.title,
                sched.kind,
                1 if sched.is_deadline else 0,
                sched.date.isoformat() if sched.date else None,
                sched.time.isoformat() if sched.time else None,
                sched.raw_date_text,
                now,
            ),
        )
    conn.commit()
    return event_id


def _schedules_for_event(conn: sqlite3.Connection, event_id: int) -> list[ScheduleRow]:
    rows = conn.execute(
        "SELECT id, title, kind, is_deadline, date, time, raw_date_text "
        "FROM schedules WHERE event_id = ? ORDER BY date IS NULL, date, id",
        (event_id,),
    ).fetchall()
    return [
        ScheduleRow(
            id=row["id"],
            title=row["title"],
            kind=row["kind"],
            is_deadline=bool(row["is_deadline"]),
            date=row["date"],
            time=row["time"],
            raw_date_text=row["raw_date_text"],
        )
        for row in rows
    ]


def list_events(conn: sqlite3.Connection) -> list[EventRow]:
    """全イベントを新しい順に、配下の予定込みで返す。"""
    rows = conn.execute(
        "SELECT id, title, source_kind, note, commit_state FROM events "
        "ORDER BY created_at DESC, id DESC"
    ).fetchall()
    return [
        EventRow(
            id=row["id"],
            title=row["title"],
            source_kind=row["source_kind"],
            note=row["note"],
            commit_state=row["commit_state"],
            schedules=_schedules_for_event(conn, row["id"]),
        )
        for row in rows
    ]
