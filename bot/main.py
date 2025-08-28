import os, asyncio, json
from typing import Optional
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
if not BOT_TOKEN or not WEBAPP_URL:
    raise RuntimeError("Need BOT_TOKEN and WEBAPP_URL")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
LAST_MSG: dict[int, int] = {}

def inline_open_kb(ref_code: Optional[str] = None) -> InlineKeyboardMarkup:
    url = WEBAPP_URL
    if ref_code:
        url += ("&" if "?" in url else "?") + f"ref={ref_code}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть магазин", web_app=WebAppInfo(url=url))]
    ])

def extract_start_payload(m: Message) -> str:
    if not m.text: return ""
    parts = m.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

@dp.message(CommandStart())
async def cmd_start(m: Message):
    ref = extract_start_payload(m)
    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid:
            await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except Exception:
        pass
    msg = await m.answer(
        "Добро пожаловать в магазин Rumus! Откройте мини-приложение:",
        reply_markup=inline_open_kb(ref_code=ref)
    )
    LAST_MSG[m.from_user.id] = msg.message_id

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    try:
        data = json.loads(m.web_app_data.data)
    except Exception:
        data = {"raw": m.web_app_data.data}
    await m.answer(f"📦 MiniApp: <code>{json.dumps(data, ensure_ascii=False)}</code>")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
