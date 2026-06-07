"""Gemini を使った抽出（ADR-0002 の本物実装の一つ）。

GEMINI_API_KEY が必要。鍵が無い場合は構築時にエラーにする（呼び出し側でダミーに退避）。
API を叩く部分と、応答を ExtractionResult に写す純粋部分（_to_result）を分けてある。
"""

from __future__ import annotations

import os
from datetime import date, time

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.extraction.adapter import (
    ExtractedSchedule,
    ExtractionInput,
    ExtractionResult,
)

_DEFAULT_MODEL = "gemini-2.5-flash"


class _SchedulePayload(BaseModel):
    title: str
    kind: str | None = None
    is_deadline: bool = False
    date: str | None = None
    time: str | None = None
    raw_date_text: str | None = None


class _EventPayload(BaseModel):
    event_title: str
    schedules: list[_SchedulePayload] = []


def _prompt(today: date) -> str:
    return (
        "あなたは募集・案内のテキストや画像から予定を抽出するアシスタント。"
        f"今日は {today.isoformat()}。結果は指定スキーマの JSON で返す。\n"
        "- event_title: 入力が表す募集・案件の短い名前\n"
        "- schedules: 日付に関わる項目の配列。各要素は\n"
        "  - title: その予定の短い名前（例: 応募締切）\n"
        "  - kind: 種類ラベル（例: 応募締切 / 面接 / 説明会）\n"
        "  - is_deadline: 締切なら true\n"
        "  - date: YYYY-MM-DD。年が無ければ今日以降で最も近い年。"
        "具体的な日が不明なら null\n"
        "  - time: HH:MM。不明なら null\n"
        "  - raw_date_text: 元の日付表現（例: 7月中 / 後日発表）\n"
        "日付がまったく無い入力なら schedules は空配列にする。"
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _to_result(payload: _EventPayload) -> ExtractionResult:
    return ExtractionResult(
        event_title=payload.event_title or "取り込み",
        schedules=[
            ExtractedSchedule(
                title=item.title,
                is_deadline=item.is_deadline,
                kind=item.kind,
                date=_parse_date(item.date),
                time=_parse_time(item.time),
                raw_date_text=item.raw_date_text,
            )
            for item in payload.schedules
        ],
    )


def _build_contents(source: ExtractionInput, today: date) -> list[str | types.Part]:
    contents: list[str | types.Part] = [_prompt(today)]
    if source.kind == "image" and source.image is not None:
        mime = source.image_mime or "image/png"
        contents.append(types.Part.from_bytes(data=source.image, mime_type=mime))
    else:
        contents.append(source.text or "")
    return contents


class GeminiExtractor:
    """ExtractionAdapter を満たす Gemini 実装。"""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY が設定されていない")
        self._client = genai.Client(api_key=api_key)
        self._model = model or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)

    def extract(self, source: ExtractionInput, today: date) -> ExtractionResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=_build_contents(source, today),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_EventPayload,
            ),
        )
        payload = response.parsed
        if not isinstance(payload, _EventPayload):
            raise RuntimeError("Gemini 応答を構造化できなかった")
        return _to_result(payload)
