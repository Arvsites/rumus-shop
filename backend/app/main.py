# backend/app/main.py
from __future__ import annotations

import os
import uuid
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Rumus Backend", version="1.0.0")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


class InlineAnswerIn(BaseModel):
    query_id: str
    data: dict


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/inline_answer")
async def inline_answer(body: InlineAnswerIn):
    """
    Для inline‑кнопки: получаем query_id и данные из Mini App,
    отвечаем в чат через answerWebAppQuery.
    """
    # result.id должен быть уникальным
    result = {
        "type": "article",
        "id": str(uuid.uuid4()),
        "title": "Данные из Mini App",
        "input_message_content": {
            "message_text": f"📦 {body.data}"
        }
    }

    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/answerWebAppQuery",
            json={
                "web_app_query_id": body.query_id,
                "result": result,
            },
        )

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)

    return JSONResponse(r.json())
