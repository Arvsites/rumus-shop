from pathlib import Path
import os, json
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

app = FastAPI(title="Rumus Mini App")

# Статика
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
async def index(_: Request) -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


# ---- Поддержка answerWebAppQuery ----
BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None


class AnswerIn(BaseModel):
    query_id: str
    data: dict


@app.post("/api/webapp/answer")
async def api_webapp_answer(in_: AnswerIn):
    if not TG_API:
        return {"ok": False, "description": "BOT_TOKEN не задан"}
    payload_text = json.dumps(in_.data, ensure_ascii=False, indent=2)
    body = {
        "web_app_query_id": in_.query_id,
        "result": {
            "type": "article",
            "id": str(uuid4()),
            "title": "Данные получены",
            "input_message_content": {
                "message_text": f"📦 Из Mini App:\n{payload_text}"
            },
        },
    }
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.post(f"{TG_API}/answerWebAppQuery", json=body)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "description": f"Bad TG response: {r.text}"}
