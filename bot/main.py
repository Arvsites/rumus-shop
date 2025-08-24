import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
)
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует в .env")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL отсутствует в .env")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def handle_start(m: Message):
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛍 Открыть магазин (inline)", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await m.answer("Нажми кнопку ниже, чтобы открыть Mini App.", reply_markup=inline_kb)
    await m.answer("Или используй кнопку в клавиатуре 👇", reply_markup=reply_kb)

@dp.message(F.web_app_data)
async def handle_webapp_data(m: Message):
    await m.answer(f"📦 Получено из Mini App:\n{m.web_app_data.data}")

async def _run():
    logger.info("Бот: старт polling")
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)

def main():
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен по Ctrl+C")

if __name__ == "__main__":
    main()
