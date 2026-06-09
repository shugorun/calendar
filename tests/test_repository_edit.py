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
            is_approximate=False,
            date=None,
            end_date=None,
            time=None,
            end_time=None,
        ),
    )
    updated = repository.get_event_detail(conn, event_id)
    assert updated is not None
    target = next(s for s in updated.schedules if s.id == sched.id)
    assert target.title == "応募締切（変更）"
    assert target.date is None  # 日付を空に → 日時未定


def test_update_schedule_round_trips_end_time(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    sched = next(s for s in detail.schedules if s.title == "応募締切")
    repository.update_schedule(
        conn,
        sched.id,
        repository.ScheduleFields(
            title="面談",
            kind=None,
            is_deadline=False,
            is_approximate=False,
            date="2026-06-11",
            end_date=None,
            time="14:00",
            end_time="15:00",  # 同日内の終了時刻を保持する
        ),
    )
    updated = repository.get_event_detail(conn, event_id)
    assert updated is not None
    target = next(s for s in updated.schedules if s.id == sched.id)
    assert target.time == "14:00"
    assert target.end_time == "15:00"


def test_update_schedule_round_trips_is_approximate(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    sched = next(s for s in detail.schedules if s.title == "応募締切")
    repository.update_schedule(
        conn,
        sched.id,
        repository.ScheduleFields(
            title="合否連絡",
            kind=None,
            is_deadline=False,
            is_approximate=True,  # 「6/12以降随時」のような目安
            date="2026-06-12",
            end_date=None,
            time=None,
            end_time=None,
        ),
    )
    updated = repository.get_event_detail(conn, event_id)
    assert updated is not None
    target = next(s for s in updated.schedules if s.id == sched.id)
    assert target.is_approximate is True
    assert target.date == "2026-06-12"  # 目安でも最早日に置く


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


def test_schedules_default_to_floating(conn: sqlite3.Connection) -> None:
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    assert all(s.commit_state == "floating" for s in detail.schedules)
    assert detail.committed_count == 0  # 取り込み直後はどれも浮いている


def test_set_schedule_commit_state_is_per_schedule(conn: sqlite3.Connection) -> None:
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    one = next(s for s in detail.schedules if s.title == "応募締切")
    repository.set_schedule_commit_state(conn, one.id, "committed")
    after = repository.get_event_detail(conn, detail.id)
    assert after is not None
    assert after.committed_count == 1  # 1件だけ確定、兄弟は浮いたまま
    committed = next(s for s in after.schedules if s.id == one.id)
    other = next(s for s in after.schedules if s.id != one.id)
    assert committed.commit_state == "committed"
    assert other.commit_state == "floating"
    repository.set_schedule_commit_state(conn, one.id, "floating")  # 往復で戻せる
    back = repository.get_event_detail(conn, detail.id)
    assert back is not None
    assert back.committed_count == 0


def test_commit_does_not_require_a_dated_schedule(conn: sqlite3.Connection) -> None:
    # コミット軸 ⊥ 日時の確かさ軸: 日付未定の予定でも確定にできる。
    detail = repository.get_event_detail(conn, _seed(conn))
    assert detail is not None
    undated = next(s for s in detail.schedules if s.date is None)
    repository.set_schedule_commit_state(conn, undated.id, "committed")
    after = repository.get_event_detail(conn, detail.id)
    assert after is not None
    target = next(s for s in after.schedules if s.id == undated.id)
    assert target.commit_state == "committed"
    assert target.date is None


def test_set_event_commit_state_commits_all(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    repository.set_event_commit_state(conn, event_id, "committed")  # 一括確定
    committed = repository.get_event_detail(conn, event_id)
    assert committed is not None
    assert committed.committed_count == len(committed.schedules)
    repository.set_event_commit_state(conn, event_id, "floating")  # まとめて取消
    floated = repository.get_event_detail(conn, event_id)
    assert floated is not None
    assert floated.committed_count == 0


def test_commit_state_setters_reject_unknown_value(conn: sqlite3.Connection) -> None:
    event_id = _seed(conn)
    with pytest.raises(ValueError, match="未知のコミット状態"):
        repository.set_event_commit_state(conn, event_id, "maybe")
    with pytest.raises(ValueError, match="未知のコミット状態"):
        repository.set_schedule_commit_state(conn, 1, "maybe")


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


def test_create_manual_event_with_commit_and_undated(conn: sqlite3.Connection) -> None:
    event_id = repository.create_manual_event(
        conn,
        "レアゾンHD 選考",
        [
            repository.ManualSchedule(title="一次面接", date="2026-08-20"),
            repository.ManualSchedule(
                title="最終面接", date="2026-09-05", time="10:00", committed=True
            ),
            repository.ManualSchedule(title="結果連絡"),  # 日付なし → 日時未定
        ],
    )
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.title == "レアゾンHD 選考"
    by_title = {s.title: s for s in detail.schedules}
    assert by_title["一次面接"].commit_state == "floating"
    assert by_title["最終面接"].commit_state == "committed"  # 確定チェックを反映
    assert by_title["最終面接"].time == "10:00"
    assert by_title["結果連絡"].date is None  # 日時未定


def test_manual_no_date_is_not_approximate(conn: sqlite3.Connection) -> None:
    # 目安は日付を伴う属性。日付なしで is_approximate を渡しても目安にしない。
    event_id = repository.create_manual_event(
        conn, "X", [repository.ManualSchedule(title="未定面接", is_approximate=True)]
    )
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert detail.schedules[0].date is None
    assert detail.schedules[0].is_approximate is False


def test_add_schedules_from_appends_and_keeps_source(
    conn: sqlite3.Connection,
) -> None:
    event_id = _seed(conn)  # 元入力はテキスト『〇〇インターン』、予定2件
    added = repository.add_schedules_from(
        conn,
        event_id,
        ExtractionInput(kind="image", image=b"NEW", image_mime="image/png"),
        ExtractionResult(
            event_title="無視される",
            schedules=[ExtractedSchedule(title="追加の予定", date=date(2026, 7, 1))],
        ),
    )
    assert added == 1
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    assert len(detail.schedules) == 3  # 既存2＋追加1
    assert any(s.title == "追加の予定" for s in detail.schedules)
    # 既に元入力があるイベントは上書きしない（画像は保存されない）
    assert repository.get_event_image(conn, event_id) is None


def test_add_schedules_from_sets_source_when_empty(
    conn: sqlite3.Connection,
) -> None:
    event_id = repository.create_manual_event(conn, "手動", [])  # 元入力なし
    repository.add_schedules_from(
        conn,
        event_id,
        ExtractionInput(kind="image", image=b"IMG", image_mime="image/png"),
        ExtractionResult(event_title="x", schedules=[ExtractedSchedule(title="面接")]),
    )
    got = repository.get_event_image(conn, event_id)  # 元入力が無かったので保存される
    assert got is not None
    assert got[0] == b"IMG"


def test_add_manual_schedules_appends_with_commit(conn: sqlite3.Connection) -> None:
    event_id = repository.create_manual_event(conn, "選考", [])
    added = repository.add_manual_schedules(
        conn,
        event_id,
        [
            repository.ManualSchedule(title="一次面接", date="2026-08-20"),
            repository.ManualSchedule(title="最終面接", committed=True),
        ],
    )
    assert added == 2
    detail = repository.get_event_detail(conn, event_id)
    assert detail is not None
    by_title = {s.title: s for s in detail.schedules}
    assert by_title["一次面接"].commit_state == "floating"
    assert by_title["最終面接"].commit_state == "committed"  # 確定チェックを反映
    assert by_title["最終面接"].date is None  # 日付なし → 日時未定


def test_add_manual_schedules_missing_event(conn: sqlite3.Connection) -> None:
    assert repository.add_manual_schedules(conn, 999, []) == -1


def test_add_schedules_from_missing_event(conn: sqlite3.Connection) -> None:
    n = repository.add_schedules_from(
        conn, 999, ExtractionInput(kind="text", text="x"), ExtractionResult("x", [])
    )
    assert n == -1


def test_eventless_events_lists_only_schedule_less_events(
    conn: sqlite3.Connection,
) -> None:
    with_sched = _seed(conn)  # 予定あり
    empty_id = repository.create_manual_event(conn, "予定なしイベント", [])  # 予定0件
    eventless = repository.eventless_events(conn)
    ids = {e.event_id for e in eventless}
    assert empty_id in ids  # 予定が無いイベントは出る
    assert with_sched not in ids  # 予定があるイベントは出ない
    # 全予定を消したら、そのイベントも eventless に現れる（孤児化の導線）
    detail = repository.get_event_detail(conn, with_sched)
    assert detail is not None
    for s in detail.schedules:
        repository.delete_schedule(conn, s.id)
    assert with_sched in {e.event_id for e in repository.eventless_events(conn)}


def test_undated_needs_fix_flags_unreadable_dates(conn: sqlite3.Connection) -> None:
    repository.create_event(
        conn,
        ExtractionInput(kind="text", text="ポイント"),
        ExtractionResult(
            event_title="ポイント",
            schedules=[
                ExtractedSchedule(title="失効", raw_date_text="6/31"),  # 読めない日付
                ExtractedSchedule(title="採否", raw_date_text="7月中"),  # 正当な未定
                ExtractedSchedule(title="連絡", raw_date_text="後日発表"),  # 正当な未定
                ExtractedSchedule(title="面接"),  # 原文なし
            ],
        ),
    )
    undated = {s.title: s for s in repository.undated_schedules(conn)}
    assert undated["失効"].needs_fix is True
    assert undated["採否"].needs_fix is False
    assert undated["連絡"].needs_fix is False
    assert undated["面接"].needs_fix is False
