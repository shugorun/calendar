"""build_month（月カレンダー組み立て）の振る舞いテスト。"""

from datetime import date

from app.calendar_view import build_month
from app.repository import DatedSchedule


def _sched(start: str, end: str | None = None) -> DatedSchedule:
    return DatedSchedule(
        event_id=1,
        event_title="E",
        commit_state="floating",
        title="x",
        is_deadline=False,
        date=start,
        end_date=end,
        time=None,
    )


def _days_with_schedules(view: object) -> list[date]:
    return [c.day for week in view.weeks for c in week if c.schedules]  # type: ignore[attr-defined]


def test_schedule_appears_on_its_day() -> None:
    view = build_month(2026, 6, [_sched("2026-06-15")])
    assert _days_with_schedules(view) == [date(2026, 6, 15)]


def test_range_spans_each_day() -> None:
    view = build_month(2026, 6, [_sched("2026-06-10", "2026-06-12")])
    days = _days_with_schedules(view)
    assert date(2026, 6, 10) in days
    assert date(2026, 6, 11) in days
    assert date(2026, 6, 12) in days
    assert date(2026, 6, 13) not in days


def test_prev_next_month_wrap_year() -> None:
    view = build_month(2026, 1, [])
    assert view.prev_month == "2025-12"
    assert view.next_month == "2026-02"


def test_ym_is_the_viewed_month() -> None:
    assert build_month(2026, 8, []).ym == "2026-08"


def test_in_month_flag_matches_month() -> None:
    view = build_month(2026, 6, [])
    for week in view.weeks:
        for cell in week:
            assert cell.in_month == (cell.day.month == 6)
