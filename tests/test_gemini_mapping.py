"""GeminiExtractor の応答マッピング（API を呼ばない純粋部分）のテスト。"""

from datetime import date, time

from app.extraction.gemini import (
    _DEFAULT_MODEL,
    _EventPayload,
    _resolve_model,
    _SchedulePayload,
    _to_result,
)


def test_to_result_parses_dates_times_and_flags() -> None:
    payload = _EventPayload(
        event_title="〇〇インターン",
        schedules=[
            _SchedulePayload(
                title="応募締切",
                is_deadline=True,
                date="2026-06-30",
                time="14:00",
                end_time="15:00",
                raw_date_text="6/30",
            ),
            _SchedulePayload(title="説明会", date=None, raw_date_text="7月中"),
            _SchedulePayload(title="壊れた日付", date="not-a-date"),
            _SchedulePayload(
                title="テスト期間",
                date="2026-06-25",
                end_date="2026-06-28",
                raw_date_text="6/25〜6/28",
            ),
        ],
    )
    result = _to_result(payload)

    assert result.event_title == "〇〇インターン"
    first = result.schedules[0]
    assert first.date == date(2026, 6, 30)
    assert first.time == time(14, 0)
    assert first.end_time == time(15, 0)  # 同日内の終了時刻を写す
    assert first.is_deadline is True
    assert result.schedules[1].date is None  # 日時未定はそのまま None
    assert result.schedules[2].date is None  # 壊れた日付は None に落とす
    period = result.schedules[3]
    assert period.date == date(2026, 6, 25)
    assert period.end_date == date(2026, 6, 28)  # 期間の終了日を保持


def test_empty_title_falls_back() -> None:
    result = _to_result(_EventPayload(event_title="", schedules=[]))
    assert result.event_title == "取り込み"
    assert result.schedules == []


def test_resolve_model_treats_empty_as_unset() -> None:
    # .env の GEMINI_MODEL= (空文字) でも既定にフォールバックする回帰テスト。
    assert _resolve_model(None, "") == _DEFAULT_MODEL
    assert _resolve_model(None, None) == _DEFAULT_MODEL
    assert _resolve_model(None, "gemini-x") == "gemini-x"
    assert _resolve_model("explicit", "gemini-x") == "explicit"
