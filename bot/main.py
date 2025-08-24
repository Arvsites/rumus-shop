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


# --- Конфиг из переменных окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")  # приходит из docker-compose (https://${DOMAIN})

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан (ожидался в переменных окружения).")
if not WEBAPP_URL:
    # не падаем, но предупредим
    logger.warning("WEBAPP_URL не задан — кнопка откроет пустой URL.")

# --- Инициализация бота/диспетчера ---
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# --- /start с кнопкой Mini App ---
@dp.message(CommandStart())
async def handle_start(m: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL or "https://example.com"))]
        ]
    )
    await m.answer("Привет! Нажми кнопку, чтобы открыть Mini App.", reply_markup=kb)


# --- ЛОГ всех входящих апдейтов (для диагностики) ---
@dp.update()
async def log_all_updates(upd: Update) -> None:
    try:
        # короткий JSON, чтобы не захламлять логи
        snippet = upd.model_dump_json()[:800]
        logger.info(f"UPDATE: {upd.event_type} :: {snippet}")
    except Exception as e:
        logger.error(f"Ошибка логирования апдейта: {e}")


# --- Получение данных из Mini App (WebApp.sendData) ---
@dp.message(F.web_app_data)
async def handle_webapp_data(m: Message) -> None:
    data = m.web_app_data.data  # строка JSON, отправленная из Mini App
    await m.answer(f"📦 Получено из Mini App:\n{data}")


# --- Фоллбек на обычные сообщения ---
@dp.message(F.text)
async def fallback(m: Message) -> None:
    await m.answer("Отправь /start, чтобы открыть Mini App.")


# --- Точка входа ---
async def _run() -> None:
    logger.info("Бот: старт polling")
    # На всякий очистим webhook (иначе polling не получит апдейты)
    await bot.delete_webhook(drop_pending_updates=False)
    # Явно разрешим типы апдейтов (на всякий случай)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен по Ctrl+C")
    finally:
        with suppress(Exception):
            asyncio.run(bot.session.close())


if __name__ == "__main__":
    main()
