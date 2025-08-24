import asyncio
import os
from contextlib import suppress
from typing import NoReturn

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует в .env")

# Инициализация
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def handle_start(m: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await m.answer("Привет! Нажми кнопку, чтобы открыть Mini App.", reply_markup=kb)

# Приём данных из Mini App (Telegram.WebApp.sendData)
@dp.message(F.web_app_data)
async def handle_webapp_data(m: Message) -> None:
    await m.answer(f"📦 Получено из Mini App:\n{m.web_app_data.data}")

async def _run() -> NoReturn:
    logger.info("Бот: старт polling")
    # гарантируем, что нет активного webhook (иначе polling не получит апдейты)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)

def main() -> None:
    # отдельный event loop — корректная остановка по Ctrl+C
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен по Ctrl+C")
    finally:
        # аккуратно закрываем HTTP‑клиент aiogram
        with suppress(Exception):
            asyncio.run(bot.session.close())

if __name__ == "__main__":
    main()
