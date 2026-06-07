"""月カレンダーの組み立て（純粋ロジック・DB非依存）。"""

import calendar
from dataclasses import dataclass, field
from datetime import date

from app.repository import DatedSchedule

_CAL = calendar.Calendar(firstweekday=6)  # 日曜始まり
WEEKDAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"]


@dataclass
class DayCell:
    day: date
    in_month: bool
    schedules: list[DatedSchedule] = field(default_factory=list)


@dataclass
class MonthView:
    year: int
    month: int
    weeks: list[list[DayCell]]
    prev_month: str  # "YYYY-MM"
    next_month: str


def _ym(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _covers(schedule: DatedSchedule, day: date) -> bool:
    start = date.fromisoformat(schedule.date)
    end = date.fromisoformat(schedule.end_date) if schedule.end_date else start
    if end < start:
        end = start
    return start <= day <= end


def build_month(year: int, month: int, dated: list[DatedSchedule]) -> MonthView:
    """指定月の週×日グリッドを組み立て、各日に該当予定を配置する。"""
    weeks = [
        [
            DayCell(
                day=day,
                in_month=day.month == month,
                schedules=[s for s in dated if _covers(s, day)],
            )
            for day in week
        ]
        for week in _CAL.monthdatescalendar(year, month)
    ]
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)
    return MonthView(
        year=year,
        month=month,
        weeks=weeks,
        prev_month=_ym(prev_year, prev_month),
        next_month=_ym(next_year, next_month),
    )
