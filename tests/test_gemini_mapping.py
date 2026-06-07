"""GeminiExtractor の応答マッピング（API を呼ばない純粋部分）のテスト。"""

from datetime import date, time

from app.extraction.gemini import _EventPayload, _SchedulePayload, _to_result


def test_to_result_parses_dates_times_and_flags() -> None:
    payload = _EventPayload(
        event_title="〇〇インターン",
        schedules=[
            _SchedulePayload(
                title="応募締切",
                is_deadline=True,
                date="2026-06-30",
                time="14:00",
                raw_date_text="6/30",
            ),
            _SchedulePayload(title="説明会", date=None, raw_date_text="7月中"),
            _SchedulePayload(title="壊れた日付", date="not-a-date"),
        ],
    )
    result = _to_result(payload)

    assert result.event_title == "〇〇インターン"
    first = result.schedules[0]
    assert first.date == date(2026, 6, 30)
    assert first.time == time(14, 0)
    assert first.is_deadline is True
    assert result.schedules[1].date is None  # 日時未定はそのまま None
    assert result.schedules[2].date is None  # 壊れた日付は None に落とす


def test_empty_title_falls_back() -> None:
    result = _to_result(_EventPayload(event_title="", schedules=[]))
    assert result.event_title == "取り込み"
    assert result.schedules == []
