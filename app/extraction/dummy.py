"""ダミー抽出（ADR-0002 の本物 LLM 実装に差し替えるまでの仮）。

テキストから素朴な正規表現で日付を拾うだけの仮実装。画像（スクショ）は未対応。
年は「最も近い未来」を採り、拾えなかった日付は None（＝日時未定）にする。
"""

import re
from datetime import date

from app.extraction.adapter import (
    ExtractedSchedule,
    ExtractionInput,
    ExtractionResult,
)

_DATE_RE = re.compile(r"(\d{1,2})\s*[/／月]\s*(\d{1,2})")
_DEADLINE_HINTS = ("締切", "〆", "期限", "まで")


def _nearest_future(month: int, day: int, today: date) -> date | None:
    """month/day を、今日以降で最も近い年に当てはめる。無効な日付なら None。"""
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate >= today:
            return candidate
    return None


def _schedules_from_lines(lines: list[str], today: date) -> list[ExtractedSchedule]:
    schedules: list[ExtractedSchedule] = []
    for line in lines:
        for match in _DATE_RE.finditer(line):
            month, day = int(match.group(1)), int(match.group(2))
            schedules.append(
                ExtractedSchedule(
                    title=line,
                    is_deadline=any(hint in line for hint in _DEADLINE_HINTS),
                    date=_nearest_future(month, day, today),
                    raw_date_text=match.group(0),
                )
            )
    return schedules


class DummyExtractor:
    """正規表現ベースの仮実装。ExtractionAdapter を満たす。"""

    def extract(self, source: ExtractionInput, today: date) -> ExtractionResult:
        text = (source.text or "").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        event_title = lines[0] if lines else "取り込み"
        return ExtractionResult(
            event_title=event_title,
            schedules=_schedules_from_lines(lines, today),
        )
