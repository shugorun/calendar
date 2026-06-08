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


def test_home_month_is_earliest_dated_schedule(conn: sqlite3.Connection) -> None:
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    assert detail.home_month == "2026-06"  # 応募締切 6/30 が最古、説明会は日時未定


def test_home_month_none_when_all_undated(conn: sqlite3.Connection) -> None:
    event_id = repository.create_event(
        conn,
        ExtractionInput(kind="text", text="△△"),
        ExtractionResult(
            event_title="△△",
            schedules=[ExtractedSchedule(title="締切", raw_date_text="後日発表")],
        ),
    )
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.home_month is None


def test_earliest_dated_month(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    assert repository.earliest_dated_month(conn, event_id) == "2026-06"


def test_earliest_dated_month_none_for_unknown_event(conn: sqlite3.Connection) -> None:
    assert repository.earliest_dated_month(conn, 999) is None


def test_commit_state_defaults_to_floating(conn: sqlite3.Connection) -> None:
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    assert detail.commit_state == "floating"  # 取り込み直後は浮いている


def test_set_commit_state_round_trips(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    repository.set_commit_state(conn, event_id, "committed")
    committed = repository.get_event_detail(conn, event_id)
    assert committed is not None
    assert committed.commit_state == "committed"
    repository.set_commit_state(conn, event_id, "floating")  # 往復して戻せる
    floated = repository.get_event_detail(conn, event_id)
    assert floated is not None
    assert floated.commit_state == "floating"


def test_commit_does_not_require_a_dated_schedule(conn: sqlite3.Connection) -> None:
    # コミット軸 ⊥ 日時の確かさ軸: 日付未定だけのイベントでも確定にできる。
    source = ExtractionInput(kind="text", text="△△インターン")
    event_id = repository.create_event(
        conn,
        source,
        ExtractionResult(
            event_title="△△インターン",
            schedules=[ExtractedSchedule(title="応募締切", raw_date_text="後日発表")],
        ),
    )
    repository.set_commit_state(conn, event_id, "committed")
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.commit_state == "committed"
    assert all(s.date is None for s in detail.schedules)


def test_set_commit_state_rejects_unknown_value(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="未知のコミット状態"):
        repository.set_commit_state(conn, _seed(conn), "maybe")


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
