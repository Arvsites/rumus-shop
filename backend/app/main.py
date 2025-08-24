# backend/app/main.py
from __future__ import annotations

import os
import uuid
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Rumus Backend", version="1.0.0")

# --- конфиг TG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- статика и главная страница ---
STATIC_DIR = "/app/backend/static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def index():
    # отдаём Mini App
    return FileResponse(f"{STATIC_DIR}/index.html")

@app.get("/health")
async def health():
    return {"ok": True}

# --- схема для inline‑кнопки ---
class InlineAnswerIn(BaseModel):
    query_id: str
    data: dict

@app.post("/api/inline_answer")
async def inline_answer(body: InlineAnswerIn):
    """
    Открыто через inline‑кнопку:
    бекенд вызывает answerWebAppQuery, и сообщение появляется в чате.
    """
    result = {
        "type": "article",
        "id": str(uuid.uuid4()),
        "title": "Данные из Mini App",
        "input_message_content": {"message_text": f"📦 {body.data}"}
    }

    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/answerWebAppQuery",
            json={"web_app_query_id": body.query_id, "result": result},
        )

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)

    return JSONResponse(r.json())
