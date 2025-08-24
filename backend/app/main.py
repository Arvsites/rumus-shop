import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Rumus Backend")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в переменных окружения")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- убираем 404 на корне: редирект на /health ---
@app.get("/")
async def root():
    return RedirectResponse("/health", status_code=307)

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------- models ----------
class InlineAnswerIn(BaseModel):
    query_id: str
    data: dict

class DirectMessageIn(BaseModel):
    chat_id: int
    text: str

# ---------- routes ----------
@app.post("/api/inline_answer")
async def inline_answer(body: InlineAnswerIn):
    """
    Открыто через inline‑кнопку: отвечаем в чат через answerWebAppQuery.
    """
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/answerWebAppQuery",
            data={
                "web_app_query_id": body.query_id,
                "result": {
                    "type": "article",
                    "id": "miniapp-result",
                    "title": "MiniApp response",
                    "input_message_content": {"message_text": f"📦 {body.data}"},
                },
            },
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)
    return JSONResponse(r.json())

@app.post("/api/send_message")
async def send_message(body: DirectMessageIn):
    """
    Открыто из профиля бота («Открыть»): отправляем сообщение напрямую.
    Требуется, чтобы пользователь хотя бы раз нажал /start у бота.
    """
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/sendMessage",
            data={"chat_id": body.chat_id, "text": body.text},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)
    return JSONResponse(r.json())
