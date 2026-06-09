"""未確定予定カレンダー: ローカルで動く FastAPI アプリのエントリポイント。

画面（HTML/JS）は React SPA（web/）が持ち、ここは JSON を返す API に徹する（ADR-0005）。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app import calendar_view, repository
from app.db import connect, init_db
from app.extraction import build_extractor, build_input
from app.extraction.adapter import ExtractionAdapter

BASE_DIR = Path(__file__).resolve().parent

# 抽出アダプタ（ADR-0002）。鍵があれば本物(Gemini)、無ければダミーに退避。
load_dotenv()
_extractor: ExtractionAdapter = build_extractor()


def get_extractor() -> ExtractionAdapter:
    return _extractor


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="未確定予定カレンダー", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _parse_month(value: str | None) -> tuple[int, int]:
    today = date.today()
    if value:
        parts = value.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            year, month = int(parts[0]), int(parts[1])
            if 1 <= year <= 9999 and 1 <= month <= 12:
                return year, month
    return today.year, today.month


def _norm_time(value: str) -> str | None:
    """フォームの時刻文字列を 24 時間表記 HH:MM に正規化する。空・不正は None。"""
    if not value:
        return None
    try:
        return time.fromisoformat(value).isoformat(timespec="minutes")
    except ValueError:
        return None


@app.get("/api/calendar")
def get_calendar(month: str | None = None) -> dict[str, Any]:
    """指定月の予定グリッドと、日時未定の予定をまとめて返す。"""
    year, month_num = _parse_month(month)
    conn = connect()
    try:
        dated = repository.dated_schedules(conn)
        undated = repository.undated_schedules(conn)
    finally:
        conn.close()
    view = calendar_view.build_month(year, month_num, dated)
    return {
        "view": view,
        "undated": undated,
        "weekday_labels": calendar_view.WEEKDAY_LABELS,
        "today": date.today().isoformat(),
    }


@app.post("/api/intake")
def intake(
    text: str = Form(""),
    image: UploadFile | None = File(None),
    month: str = Form(""),
    extractor: ExtractionAdapter = Depends(get_extractor),
) -> dict[str, str]:
    """取り込み: テキスト／画像から1イベントと予定を作る。表示すべき月を返す。"""
    image_bytes: bytes | None = None
    image_mime: str | None = None
    if image is not None and image.filename:
        data = image.file.read()
        if data:
            image_bytes = data
            image_mime = image.content_type

    source = build_input(text, image_bytes, image_mime)
    if source is None:
        return {"month": month}

    result = extractor.extract(source, today=date.today())
    conn = connect()
    try:
        event_id = repository.create_event(conn, source, result)
        # 取り込んだ予定がある月を表示。日付が無ければ見ていた月のまま。
        landed = repository.earliest_dated_month(conn, event_id) or month
    finally:
        conn.close()
    return {"month": landed}


@app.get("/api/events/{event_id}")
def get_event(event_id: int) -> repository.EventDetail:
    conn = connect()
    try:
        detail = repository.get_event_detail(conn, event_id)
    finally:
        conn.close()
    if detail is None:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return detail


class TitleBody(BaseModel):
    title: str


class StateBody(BaseModel):
    state: str


class NoteBody(BaseModel):
    note: str = ""


class ScheduleEditBody(BaseModel):
    title: str
    kind: str | None = None
    is_deadline: bool = False
    is_approximate: bool = False
    date: str | None = None
    end_date: str | None = None
    time: str | None = None
    end_time: str | None = None


def _check_state(state: str) -> None:
    if state not in repository.COMMIT_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知のコミット状態: {state!r}",
        )


_NO_CONTENT = Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/events/{event_id}/edit", status_code=status.HTTP_204_NO_CONTENT)
def edit_event(event_id: int, body: TitleBody) -> Response:
    conn = connect()
    try:
        repository.update_event_title(conn, event_id, body.title)
    finally:
        conn.close()
    return _NO_CONTENT


@app.post("/api/events/{event_id}/commit", status_code=status.HTTP_204_NO_CONTENT)
def commit_event(event_id: int, body: StateBody) -> Response:
    """一括確定: イベント配下の全予定をまとめて切り替える。"""
    _check_state(body.state)
    conn = connect()
    try:
        repository.set_event_commit_state(conn, event_id, body.state)
    finally:
        conn.close()
    return _NO_CONTENT


@app.post("/api/events/{event_id}/note", status_code=status.HTTP_204_NO_CONTENT)
def edit_note(event_id: int, body: NoteBody) -> Response:
    conn = connect()
    try:
        repository.update_note(conn, event_id, body.note)
    finally:
        conn.close()
    return _NO_CONTENT


@app.post("/api/events/{event_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int) -> Response:
    conn = connect()
    try:
        repository.delete_event(conn, event_id)
    finally:
        conn.close()
    return _NO_CONTENT


@app.get("/api/events/{event_id}/image")
def event_image(event_id: int) -> Response:
    conn = connect()
    try:
        image = repository.get_event_image(conn, event_id)
    finally:
        conn.close()
    if image is None:
        raise HTTPException(status_code=404, detail="画像がありません")
    data, mime = image
    return Response(content=data, media_type=mime)


@app.post("/api/schedules/{schedule_id}/commit", status_code=status.HTTP_204_NO_CONTENT)
def commit_schedule(schedule_id: int, body: StateBody) -> Response:
    _check_state(body.state)
    conn = connect()
    try:
        repository.set_schedule_commit_state(conn, schedule_id, body.state)
    finally:
        conn.close()
    return _NO_CONTENT


@app.post("/api/schedules/{schedule_id}/edit", status_code=status.HTTP_204_NO_CONTENT)
def edit_schedule(schedule_id: int, body: ScheduleEditBody) -> Response:
    fields = repository.ScheduleFields(
        title=body.title,
        kind=body.kind or None,
        is_deadline=body.is_deadline,
        is_approximate=body.is_approximate,
        date=body.date or None,
        end_date=body.end_date or None,
        time=_norm_time(body.time or ""),
        end_time=_norm_time(body.end_time or ""),
    )
    conn = connect()
    try:
        repository.update_schedule(conn, schedule_id, fields)
    finally:
        conn.close()
    return _NO_CONTENT


@app.post("/api/schedules/{schedule_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int) -> Response:
    conn = connect()
    try:
        repository.delete_schedule(conn, schedule_id)
    finally:
        conn.close()
    return _NO_CONTENT
