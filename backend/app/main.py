import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в переменных окружения")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --------- статические файлы и корень ---------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))                 # backend/app
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")        # backend/static

# /static/* будет отдавать файлы из backend/static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# корень сайта -> backend/static/index.html
@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------- MODELS ----------
class InlineAnswerIn(BaseModel):
    query_id: str
    data: dict

class DirectMessageIn(BaseModel):
    chat_id: int
    text: str

# ---------- ROUTES ----------
@app.post("/api/inline_answer")
async def inline_answer(body: InlineAnswerIn):
    """Ответ в чат через answerWebAppQuery (inline‑кнопка)."""
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/answerWebAppQuery",
            data={
                "web_app_query_id": body.query_id,
                "result": {
                    "type": "article",
                    "id": "1",
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
    """Сценарий «Открыть» (меню бота): отправляем сообщение напрямую."""
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/sendMessage",
            data={"chat_id": body.chat_id, "text": body.text},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)
    return JSONResponse(r.json())
