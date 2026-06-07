"""DummyExtractor の振る舞いテスト（日本語入力は UTF-8 ソースで安全に書く）。"""

from datetime import date

from app.extraction.adapter import ExtractionInput, ExtractionResult
from app.extraction.dummy import DummyExtractor

TODAY = date(2026, 6, 7)


def _extract(text: str) -> ExtractionResult:
    return DummyExtractor().extract(
        ExtractionInput(kind="text", text=text), today=TODAY
    )


def test_event_title_is_first_line() -> None:
    result = _extract("〇〇インターン\n応募締切 6/30")
    assert result.event_title == "〇〇インターン"


def test_deadline_flag_detected() -> None:
    result = _extract("応募締切 6/30\n一次面接 7/10")
    by_raw = {s.raw_date_text: s for s in result.schedules}
    assert by_raw["6/30"].is_deadline is True
    assert by_raw["7/10"].is_deadline is False


def test_year_is_nearest_future() -> None:
    # 6/30 は今日(6/7)以降 → 今年。1/10 は過ぎている → 来年。
    result = _extract("締切 6/30\n面接 1/10")
    by_raw = {s.raw_date_text: s for s in result.schedules}
    assert by_raw["6/30"].date == date(2026, 6, 30)
    assert by_raw["1/10"].date == date(2027, 1, 10)


def test_date_less_line_is_ignored() -> None:
    result = _extract("説明会 後日発表")
    assert result.schedules == []


def test_japanese_month_day_format() -> None:
    result = _extract("説明会 7月15日")
    assert len(result.schedules) == 1
    assert result.schedules[0].date == date(2026, 7, 15)


def test_date_range_is_captured() -> None:
    result = _extract("Webテスト 6/25〜6/28")
    assert len(result.schedules) == 1
    schedule = result.schedules[0]
    assert schedule.date == date(2026, 6, 25)
    assert schedule.end_date == date(2026, 6, 28)
