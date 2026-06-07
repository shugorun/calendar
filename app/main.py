"""未確定予定カレンダー: ローカルで動く FastAPI アプリのエントリポイント。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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


@app.get("/", response_class=HTMLResponse)
def index(request: Request, month: str | None = None) -> HTMLResponse:
    year, month_num = _parse_month(month)
    conn = connect()
    try:
        dated = repository.dated_schedules(conn)
        undated = repository.undated_schedules(conn)
    finally:
        conn.close()
    view = calendar_view.build_month(year, month_num, dated)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "未確定予定カレンダー",
            "view": view,
            "undated": undated,
            "weekday_labels": calendar_view.WEEKDAY_LABELS,
            "today": date.today().isoformat(),
        },
    )


@app.post("/intake")
def intake(
    text: str = Form(""),
    image: UploadFile | None = File(None),
    extractor: ExtractionAdapter = Depends(get_extractor),
) -> RedirectResponse:
    image_bytes: bytes | None = None
    image_mime: str | None = None
    if image is not None and image.filename:
        data = image.file.read()
        if data:
            image_bytes = data
            image_mime = image.content_type

    source = build_input(text, image_bytes, image_mime)
    if source is None:
        return RedirectResponse(url="/", status_code=303)

    result = extractor.extract(source, today=date.today())
    conn = connect()
    try:
        repository.create_event(conn, source, result)
    finally:
        conn.close()
    return RedirectResponse(url="/", status_code=303)
