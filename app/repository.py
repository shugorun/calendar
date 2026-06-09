"""events / schedules の保存・取得（ADR-0004: 識別は内部ID、名前はユーザー所有）。"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.extraction.adapter import ExtractionInput, ExtractionResult

# 「M/D」「M月D日」など日付らしい表記。未定なのに残る＝読めなかった日付。
_DATEISH_RE = re.compile(r"\d{1,2}\s*[/／月]\s*\d{1,2}")


def _looks_like_unreadable_date(raw: str | None) -> bool:
    """raw_date_text が具体的な日付表記なのに置けていない（例「6/31」）＝要確認。"""
    return raw is not None and _DATEISH_RE.search(raw) is not None


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
    needs_fix: bool  # 読めない日付（例「6/31」）が残っている＝日付の確認を促す


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


@dataclass
class ManualSchedule:
    """手動追加フォームの1予定。AI 抽出を介さず、確定状態も持つ。"""

    title: str
    date: str | None = None
    end_date: str | None = None
    time: str | None = None
    end_time: str | None = None
    is_deadline: bool = False
    is_approximate: bool = False
    committed: bool = False


def create_manual_event(
    conn: sqlite3.Connection, title: str, schedules: list[ManualSchedule]
) -> int:
    """手動入力でイベント1件＋予定を作る（元入力は持たない＝source_kind='text'）。"""
    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO events (title, source_kind, source_text, source_image, "
        "source_image_mime, created_at) VALUES (?, 'text', NULL, NULL, NULL, ?)",
        (title, now),
    )
    event_id = cur.lastrowid
    if event_id is None:
        raise RuntimeError("events への INSERT で id が取得できなかった")
    for s in schedules:
        # 目安は日付を伴う属性（CONTEXT）。日付が無ければ目安にしない。
        is_approximate = s.is_approximate and s.date is not None
        conn.execute(
            "INSERT INTO schedules "
            "(event_id, title, kind, is_deadline, is_approximate, date, end_date, "
            "time, end_time, raw_date_text, commit_state, created_at) "
            "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            (
                event_id,
                s.title,
                1 if s.is_deadline else 0,
                1 if is_approximate else 0,
                s.date,
                s.end_date,
                s.time,
                s.end_time,
                "committed" if s.committed else "floating",
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
            needs_fix=_looks_like_unreadable_date(row["raw_date_text"]),
        )
        for row in rows
    ]


@dataclass
class EventlessEvent:
    """予定が1件も無いイベント。カレンダーにも未定にも出ないので導線が要る。"""

    event_id: int
    event_title: str


def eventless_events(conn: sqlite3.Connection) -> list[EventlessEvent]:
    """予定を1件も持たないイベント（取り込んだが日付が拾えなかった等）を返す。"""
    rows = conn.execute(
        "SELECT e.id, e.title FROM events e "
        "WHERE NOT EXISTS (SELECT 1 FROM schedules s WHERE s.event_id = e.id) "
        "ORDER BY e.id"
    ).fetchall()
    return [
        EventlessEvent(event_id=row["id"], event_title=row["title"]) for row in rows
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


def add_manual_schedules(
    conn: sqlite3.Connection, event_id: int, schedules: list[ManualSchedule]
) -> int:
    """既存イベントに手動入力の予定を追加。返り値=追加件数。イベントが無ければ -1。"""
    exists = conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone()
    if exists is None:
        return -1
    now = _now_iso()
    for s in schedules:
        # 目安は日付を伴う属性（CONTEXT）。日付が無ければ目安にしない。
        is_approximate = s.is_approximate and s.date is not None
        conn.execute(
            "INSERT INTO schedules "
            "(event_id, title, kind, is_deadline, is_approximate, date, end_date, "
            "time, end_time, raw_date_text, commit_state, created_at) "
            "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            (
                event_id,
                s.title,
                1 if s.is_deadline else 0,
                1 if is_approximate else 0,
                s.date,
                s.end_date,
                s.time,
                s.end_time,
                "committed" if s.committed else "floating",
                now,
            ),
        )
    conn.commit()
    return len(schedules)


def add_schedules_from(
    conn: sqlite3.Connection,
    event_id: int,
    source: ExtractionInput,
    result: ExtractionResult,
) -> int:
    """既存イベントに抽出結果の予定を追加する。元入力が無ければこの入力を保存。

    返り値は追加した予定数。イベントが無ければ -1。
    """
    ev = conn.execute(
        "SELECT source_image, source_text FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if ev is None:
        return -1
    now = _now_iso()
    # 元入力（画像/テキスト）が未保存のイベントなら、今回の入力を元入力として残す。
    if ev["source_image"] is None and not ev["source_text"]:
        conn.execute(
            "UPDATE events SET source_kind = ?, source_text = ?, "
            "source_image = ?, source_image_mime = ? WHERE id = ?",
            (source.kind, source.text, source.image, source.image_mime, event_id),
        )
    for sched in result.schedules:
        is_approximate = sched.is_approximate and sched.date is not None
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
                1 if is_approximate else 0,
                sched.date.isoformat() if sched.date else None,
                sched.end_date.isoformat() if sched.end_date else None,
                sched.time.isoformat() if sched.time else None,
                sched.end_time.isoformat() if sched.end_time else None,
                sched.raw_date_text,
                now,
            ),
        )
    conn.commit()
    return len(result.schedules)


def add_blank_schedule(conn: sqlite3.Connection, event_id: int) -> int | None:
    """既存イベントに空（タイトル無し・日時未定・浮いている）の予定を1件足す。

    その場でインライン編集する前提。イベントが無ければ None。
    """
    exists = conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone()
    if exists is None:
        return None
    cur = conn.execute(
        "INSERT INTO schedules (event_id, title, created_at) VALUES (?, '', ?)",
        (event_id, _now_iso()),
    )
    conn.commit()
    return cur.lastrowid


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
