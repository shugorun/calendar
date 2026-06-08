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
    is_approximate: bool
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
            "(event_id, title, kind, is_deadline, is_approximate, date, end_date, "
            "time, end_time, raw_date_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                sched.title,
                sched.kind,
                1 if sched.is_deadline else 0,
                1 if sched.is_approximate else 0,
                sched.date.isoformat() if sched.date else None,
                sched.end_date.isoformat() if sched.end_date else None,
                sched.time.isoformat() if sched.time else None,
                sched.end_time.isoformat() if sched.end_time else None,
                sched.raw_date_text,
                now,
            ),
        )
    conn.commit()
    return event_id


def earliest_dated_month(conn: sqlite3.Connection, event_id: int) -> str | None:
    """イベント配下で最も早い日付の月 "YYYY-MM"。日付付き予定が無ければ None。"""
    row = conn.execute(
        "SELECT MIN(date) AS d FROM schedules WHERE event_id = ? AND date IS NOT NULL",
        (event_id,),
    ).fetchone()
    return row["d"][:7] if row and row["d"] else None


def dated_schedules(conn: sqlite3.Connection) -> list[DatedSchedule]:
    """日付を持つ全予定を、イベント情報込みで返す。"""
    rows = conn.execute(
        "SELECT s.event_id, e.title AS event_title, s.commit_state, "
        "s.title, s.is_deadline, s.is_approximate, s.date, s.end_date, s.time "
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
            is_approximate=bool(row["is_approximate"]),
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


@dataclass
class EditableSchedule:
    id: int
    title: str
    kind: str | None
    is_deadline: bool
    is_approximate: bool
    date: str | None
    end_date: str | None
    time: str | None
    end_time: str | None
    raw_date_text: str | None
    commit_state: str


@dataclass
class EventDetail:
    id: int
    title: str
    source_kind: str
    note: str
    has_image: bool
    source_text: str | None
    schedules: list[EditableSchedule]
    committed_count: int  # 配下で確定済みの予定数（一括確定UIの判定用）
    home_month: str | None  # 最初の日付の月 "YYYY-MM"。日付付き予定が無ければ None


@dataclass
class ScheduleFields:
    """予定の編集で書き換える項目。date/end_date/time/end_time は ISO 文字列か None。"""

    title: str
    kind: str | None
    is_deadline: bool
    is_approximate: bool
    date: str | None
    end_date: str | None
    time: str | None
    end_time: str | None


def get_event_detail(conn: sqlite3.Connection, event_id: int) -> EventDetail | None:
    """1イベントを編集用の全項目込みで返す。無ければ None。"""
    ev = conn.execute(
        "SELECT id, title, source_kind, note, source_text, "
        "(source_image IS NOT NULL) AS has_image FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if ev is None:
        return None
    rows = conn.execute(
        "SELECT id, title, kind, is_deadline, is_approximate, date, end_date, "
        "time, end_time, raw_date_text, commit_state "
        "FROM schedules WHERE event_id = ? ORDER BY date IS NULL, date, id",
        (event_id,),
    ).fetchall()
    schedules = [
        EditableSchedule(
            id=row["id"],
            title=row["title"],
            kind=row["kind"],
            is_deadline=bool(row["is_deadline"]),
            is_approximate=bool(row["is_approximate"]),
            date=row["date"],
            end_date=row["end_date"],
            time=row["time"],
            end_time=row["end_time"],
            raw_date_text=row["raw_date_text"],
            commit_state=row["commit_state"],
        )
        for row in rows
    ]
    dated = [s.date for s in schedules if s.date]
    return EventDetail(
        id=ev["id"],
        title=ev["title"],
        source_kind=ev["source_kind"],
        note=ev["note"],
        has_image=bool(ev["has_image"]),
        source_text=ev["source_text"],
        schedules=schedules,
        committed_count=sum(1 for s in schedules if s.commit_state == "committed"),
        home_month=min(dated)[:7] if dated else None,
    )


def update_event_title(conn: sqlite3.Connection, event_id: int, title: str) -> None:
    conn.execute("UPDATE events SET title = ? WHERE id = ?", (title, event_id))
    conn.commit()


COMMIT_STATES = ("floating", "committed")


def _check_commit_state(state: str) -> None:
    if state not in COMMIT_STATES:
        raise ValueError(f"未知のコミット状態: {state!r}（{COMMIT_STATES} のいずれか）")


def set_schedule_commit_state(
    conn: sqlite3.Connection, schedule_id: int, state: str
) -> None:
    """1予定のコミット軸を設定する（往復可能。CONTEXT: 確定↔浮いている）。"""
    _check_commit_state(state)
    conn.execute(
        "UPDATE schedules SET commit_state = ? WHERE id = ?", (state, schedule_id)
    )
    conn.commit()


def set_event_commit_state(conn: sqlite3.Connection, event_id: int, state: str) -> None:
    """イベント配下の全予定をまとめて確定／浮いているにする（一括確定）。"""
    _check_commit_state(state)
    conn.execute(
        "UPDATE schedules SET commit_state = ? WHERE event_id = ?", (state, event_id)
    )
    conn.commit()


def delete_event(conn: sqlite3.Connection, event_id: int) -> None:
    """イベントを削除する。配下の予定も ON DELETE CASCADE で消える。"""
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()


def update_schedule(
    conn: sqlite3.Connection, schedule_id: int, fields: ScheduleFields
) -> None:
    conn.execute(
        "UPDATE schedules SET title = ?, kind = ?, is_deadline = ?, "
        "is_approximate = ?, date = ?, end_date = ?, time = ?, end_time = ? "
        "WHERE id = ?",
        (
            fields.title,
            fields.kind,
            1 if fields.is_deadline else 0,
            1 if fields.is_approximate else 0,
            fields.date,
            fields.end_date,
            fields.time,
            fields.end_time,
            schedule_id,
        ),
    )
    conn.commit()


def delete_schedule(conn: sqlite3.Connection, schedule_id: int) -> None:
    conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()


def update_note(conn: sqlite3.Connection, event_id: int, note: str) -> None:
    conn.execute("UPDATE events SET note = ? WHERE id = ?", (note, event_id))
    conn.commit()


def get_event_image(
    conn: sqlite3.Connection, event_id: int
) -> tuple[bytes, str] | None:
    """イベントの元画像と MIME を返す。画像が無ければ None。"""
    row = conn.execute(
        "SELECT source_image, source_image_mime FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if row is None or row["source_image"] is None:
        return None
    return row["source_image"], row["source_image_mime"] or "image/png"
