"""イベント・予定の取得/編集/削除（永続化の振る舞い）テスト。"""

import sqlite3
from datetime import date

import pytest

from app import repository
from app.db import _SCHEMA
from app.extraction.adapter import ExtractedSchedule, ExtractionInput, ExtractionResult


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA)
    return connection


def _seed(conn: sqlite3.Connection) -> int:
    source = ExtractionInput(kind="text", text="〇〇インターン")
    result = ExtractionResult(
        event_title="〇〇インターン",
        schedules=[
            ExtractedSchedule(
                title="応募締切", is_deadline=True, date=date(2026, 6, 30)
            ),
            ExtractedSchedule(title="説明会", raw_date_text="後日発表"),
        ],
    )
    return repository.create_event(conn, source, result)


def test_get_event_detail(conn: sqlite3.Connection) -> None:
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    assert detail.title == "〇〇インターン"
    assert len(detail.schedules) == 2


def test_get_event_detail_missing(conn: sqlite3.Connection) -> None:
    assert repository.get_event_detail(conn, 999) is None


def test_update_schedule_clears_date_to_unknown(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    sched = next(s for s in detail.schedules if s.title == "応募締切")
    repository.update_schedule(
        conn,
        sched.id,
        repository.ScheduleFields(
            title="応募締切（変更）",
            kind=None,
            is_deadline=True,
            date=None,
            end_date=None,
            time=None,
        ),
    )
    updated = repository.get_event_detail(conn, event_id)
    assert updated is not None
    target = next(s for s in updated.schedules if s.id == sched.id)
    assert target.title == "応募締切（変更）"
    assert target.date is None  # 日付を空に → 日時未定


def test_delete_schedule(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    repository.delete_schedule(conn, detail.schedules[0].id)
    after = repository.get_event_detail(conn, event_id)
    assert after is not None
    assert len(after.schedules) == 1


def test_update_event_title(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    repository.update_event_title(conn, event_id, "新しい名前")
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.title == "新しい名前"


def test_delete_event_cascades(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    repository.delete_event(conn, event_id)
    assert repository.get_event_detail(conn, event_id) is None
    remaining = conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
    assert remaining == 0  # ON DELETE CASCADE で予定も消える


def test_update_note(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    repository.update_note(conn, event_id, "一週間前に準備")
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.note == "一週間前に準備"


def test_get_event_image_for_image_event(conn: sqlite3.Connection) -> None:
    source = ExtractionInput(
        kind="image", image=b"PNGDATA", image_mime="image/png", text="PACLIC"
    )
    event_id = repository.create_event(
        conn, source, ExtractionResult(event_title="PACLIC", schedules=[])
    )
    got = repository.get_event_image(conn, event_id)
    assert got is not None
    data, mime = got
    assert data == b"PNGDATA"
    assert mime == "image/png"


def test_get_event_image_none_for_text_event(conn: sqlite3.Connection) -> None:
    assert repository.get_event_image(conn, _seed(conn)) is None
