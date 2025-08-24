import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---- Статика ----
# ожидаем файл backend/static/index.html
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")

@app.get("/")
async def root():
    if not os.path.exists(INDEX_HTML):
        raise HTTPException(status_code=500, detail="index.html not found")
    return FileResponse(INDEX_HTML)

@app.get("/health")
async def health():
    return {"ok": True}

# ---- API для answerWebAppQuery (для запуска из скрепки) ----
class AnswerPayload(BaseModel):
    query_id: str
    text: str

@app.post("/api/webapp/answer")
async def webapp_answer(p: AnswerPayload):
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
    j = r.json()
    if r.status_code != 200 or not j.get("ok"):
        raise HTTPException(status_code=500, detail=f"Telegram error: {r.text}")
    return {"ok": True}
