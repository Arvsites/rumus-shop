from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

class AnswerPayload(BaseModel):
    query_id: str
    text: str

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/webapp/answer")
async def webapp_answer(p: AnswerPayload):
    """
    Для запуска из Attachment Menu (есть query_id):
    отправляем сообщение от имени Web App через answerWebAppQuery.
    """
    data = {
        "web_app_query_id": p.query_id,
        "result": {
            "type": "article",
            "id": "msg-1",
            "title": "Данные из Mini App",
            "input_message_content": {"message_text": f"📦 {p.text}"},
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{TELEGRAM_API}/answerWebAppQuery", json=data)
    if r.status_code != 200 or not r.json().get("ok"):
        raise HTTPException(status_code=500, detail=f"Telegram error: {r.text}")
    return {"ok": True}
