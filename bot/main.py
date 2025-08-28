import os
import asyncio
import json
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# === ENV ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")  # например: https://92-51-22-168.sslip.io
if not BOT_TOKEN or not WEBAPP_URL:
    raise RuntimeError("Need BOT_TOKEN and WEBAPP_URL in environment")

# === BOT/DP ===
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# храним id последнего сообщения для «активного модуля» (зачистка при переходах)
LAST_MSG: dict[int, int] = {}  # tg_user_id -> message_id


def main_menu_kb(ref_code: Optional[str] = None) -> ReplyKeyboardMarkup:
    """
    Кнопка открытия Mini App. Если есть реф-код, прокидываем его в URL (?ref=...)
    чтобы фронт мог подставить referral_code при регистрации.
    """
    url = WEBAPP_URL
    if ref_code:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ref={ref_code}"

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открыть магазин", web_app=WebAppInfo(url=url))],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )


def extract_start_payload(m: Message) -> str:
    """
    Извлекаем payload из deep-link: /start <payload>.
    Примеры текста:
      "/start" -> ""
      "/start abc123" -> "abc123"
    """
    if not m.text:
        return ""
    parts = m.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@dp.message(CommandStart())
async def cmd_start(m: Message):
    # реферальный код из deep-link
    ref = extract_start_payload(m)

    # чистим предыдущее активное сообщение
    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid:
            await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except Exception:
        pass

    msg = await m.answer(
        "Добро пожаловать! Откройте мини-приложение 👇",
        reply_markup=main_menu_kb(ref_code=ref)
    )
    LAST_MSG[m.from_user.id] = msg.message_id


@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    """
    Обработка данных, присланных Mini App через tg.sendData().
    Просто логируем в чат для отладки.
    """
    try:
        data = json.loads(m.web_app_data.data)
    except Exception:
        data = {"raw": m.web_app_data.data}

    await m.answer(
        f"📦 Получено из MiniApp: <code>{json.dumps(data, ensure_ascii=False)}</code>",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(F.text == "Назад")
async def back_to_menu(m: Message):
    """
    Возврат в главное меню и зачистка предыдущего активного сообщения.
    """
    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid:
            await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except Exception:
        pass

    msg = await m.answer("Главное меню", reply_markup=main_menu_kb())
    LAST_MSG[m.from_user.id] = msg.message_id


async def main():
    # Если раньше стоял вебхук — его можно сбросить вручную:
    # await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
