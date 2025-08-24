# bot/main.py
import asyncio
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    Update,
)
from loguru import logger


BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан.")
if not WEBAPP_URL:
    logger.warning("WEBAPP_URL не задан — кнопка откроет example.com")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def handle_start(m: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🛍 Открыть магазин",
            web_app=WebAppInfo(url=WEBAPP_URL or "https://example.com"),
        )
    ]])
    await m.answer("Привет! Нажми кнопку, чтобы открыть Mini App.", reply_markup=kb)


# 0) ЛОГИРУЕМ КАЖДЫЙ АПДЕЙТ (любой)
@dp.update()
async def log_all(upd: Update) -> None:
    snippet = upd.model_dump_json()[:1200]
    logger.info(f"UPDATE [{upd.event_type}]: {snippet}")


# 1) ЯВНО ЛОВИМ web_app_data
@dp.message(F.web_app_data)
async def on_webapp_data(m: Message) -> None:
    await m.answer(f"📦 Получено из Mini App:\n{m.web_app_data.data}")


# 2) ЛОВИМ ЛЮБОЕ message и говорим его тип (диагностика)
@dp.message()
async def on_any_message(m: Message) -> None:
    logger.info(f"MSG type={m.content_type}")
    # чтобы было видно, что бот видит сообщения
    if m.content_type != "web_app_data":
        await m.answer(f"Я вижу сообщение типа: {m.content_type}. Отправь /start для кнопки.")


async def _run() -> None:
    me = await bot.get_me()
    logger.info(f"Бот запущен: @{me.username} (id={me.id})")
    # снимаем webhook, чтобы polling получал апдейты
    await bot.delete_webhook(drop_pending_updates=False)
    # без ограничений по типам апдейтов — пусть прилетает всё
    await dp.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Остановлен по Ctrl+C")
    finally:
        with suppress(Exception):
            asyncio.run(bot.session.close())


if __name__ == "__main__":
    main()
