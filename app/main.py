"""未確定予定カレンダー: ローカルで動く FastAPI アプリのエントリポイント。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import repository
from app.db import connect, init_db
from app.extraction import build_extractor
from app.extraction.adapter import ExtractionAdapter, ExtractionInput

BASE_DIR = Path(__file__).resolve().parent

# 抽出アダプタ（ADR-0002）。鍵があれば本物(Gemini)、無ければダミーに退避。
load_dotenv()
extractor: ExtractionAdapter = build_extractor()


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


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    conn = connect()
    try:
        events = repository.list_events(conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        request, "index.html", {"title": "未確定予定カレンダー", "events": events}
    )


@app.post("/intake")
def intake(text: str = Form("")) -> RedirectResponse:
    source = ExtractionInput(kind="text", text=text)
    result = extractor.extract(source, today=date.today())
    conn = connect()
    try:
        repository.create_event(conn, source, result)
    finally:
        conn.close()
    return RedirectResponse(url="/", status_code=303)
