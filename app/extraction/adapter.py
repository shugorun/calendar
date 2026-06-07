"""抽出アダプタのインターフェースと結果型（ADR-0002: プロバイダ差し替え可能）。

取り込んだ入力（テキスト／画像）から、イベントのタイトルと予定の候補を作る。
本物の Vision LLM 実装も、ダミー実装も、この ExtractionAdapter を満たす。
"""

import datetime
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExtractionInput:
    """取り込みの元入力。kind は 'text' か 'image'。"""

    kind: str
    text: str | None = None
    image: bytes | None = None
    image_mime: str | None = None


@dataclass
class ExtractedSchedule:
    """抽出された1件の予定候補。date が None なら日時未定。"""

    title: str
    is_deadline: bool = False
    kind: str | None = None
    date: datetime.date | None = None
    end_date: datetime.date | None = None
    time: datetime.time | None = None
    raw_date_text: str | None = None


@dataclass
class ExtractionResult:
    """1回の取り込みの抽出結果（1イベント＋その予定候補）。"""

    event_title: str
    schedules: list[ExtractedSchedule] = field(default_factory=list)


class ExtractionAdapter(Protocol):
    def extract(
        self, source: ExtractionInput, today: datetime.date
    ) -> ExtractionResult: ...
