"""events / schedules の保存・取得（ADR-0004: 識別は内部ID、名前はユーザー所有）。"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.extraction.adapter import ExtractionInput, ExtractionResult


@dataclass
class DatedSchedule:
    """日付を持つ予定（カレンダーに置ける）。イベント情報を含む。"""

    event_id: int
    event_title: str
    commit_state: str
    title: str
    is_deadline: bool
    date: str
    end_date: str | None
    time: str | None


@dataclass
class UndatedSchedule:
    """日時未定の予定（カレンダーに置けない）。イベント情報を含む。"""

    event_id: int
    event_title: str
    title: str
    raw_date_text: str | None


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
            "(event_id, title, kind, is_deadline, date, end_date, time, "
            "raw_date_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                sched.title,
                sched.kind,
                1 if sched.is_deadline else 0,
                sched.date.isoformat() if sched.date else None,
                sched.end_date.isoformat() if sched.end_date else None,
                sched.time.isoformat() if sched.time else None,
                sched.raw_date_text,
                now,
            ),
        )
    conn.commit()
    return event_id


def dated_schedules(conn: sqlite3.Connection) -> list[DatedSchedule]:
    """日付を持つ全予定を、イベント情報込みで返す。"""
    rows = conn.execute(
        "SELECT s.event_id, e.title AS event_title, e.commit_state, "
        "s.title, s.is_deadline, s.date, s.end_date, s.time "
        "FROM schedules s JOIN events e ON e.id = s.event_id "
        "WHERE s.date IS NOT NULL ORDER BY s.date, s.id"
    ).fetchall()
    return [
        DatedSchedule(
            event_id=row["event_id"],
            event_title=row["event_title"],
            commit_state=row["commit_state"],
            title=row["title"],
            is_deadline=bool(row["is_deadline"]),
            date=row["date"],
            end_date=row["end_date"],
            time=row["time"],
        )
        for row in rows
    ]


def undated_schedules(conn: sqlite3.Connection) -> list[UndatedSchedule]:
    """日時未定の全予定を、イベント情報込みで返す。"""
    rows = conn.execute(
        "SELECT s.event_id, e.title AS event_title, s.title, s.raw_date_text "
        "FROM schedules s JOIN events e ON e.id = s.event_id "
        "WHERE s.date IS NULL ORDER BY s.id"
    ).fetchall()
    return [
        UndatedSchedule(
            event_id=row["event_id"],
            event_title=row["event_title"],
            title=row["title"],
            raw_date_text=row["raw_date_text"],
        )
        for row in rows
    ]
