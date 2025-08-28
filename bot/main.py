import os
import asyncio
import json
import smtplib, ssl
from email.mime.text import MIMEText

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# === ENV ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Данные для Яндекс.Почты
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))  # для SSL у Яндекса обычно 465
SMTP_USER = os.getenv("SMTP_USER")  # ваш яндекс-аккаунт (например, mybot@yandex.ru)
SMTP_PASS = os.getenv("SMTP_PASS")  # пароль приложения Яндекса
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "arvsites@mail.ru")

if not BOT_TOKEN or not WEBAPP_URL or not SMTP_USER or not SMTP_PASS:
    raise RuntimeError("Необходимо задать BOT_TOKEN, WEBAPP_URL, SMTP_USER, SMTP_PASS в .env")

# === BOT/DP ===
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
LAST_MSG: dict[int, int] = {}


def build_inline_kb(ref_code: str | None = None) -> InlineKeyboardMarkup:
    """
    Inline-кнопка для открытия MiniApp.
    """
    url = WEBAPP_URL
    if ref_code:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ref={ref_code}"

    kb = [[InlineKeyboardButton(text="Открыть магазин", web_app=WebAppInfo(url=url))]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def send_email(order_number: str, total_cents: int, items: list):
    """
    Отправка письма через SMTP Яндекс (порт 465, SSL).
    """
    body = f"Новый заказ №{order_number}\nИтого: {total_cents/100:.2f} ₽\n\n"
    for i in items:
        body += f"- {i['title']} × {i['qty']} = {i['price_cents']/100:.2f} ₽\n"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Новый заказ {order_number}"
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def extract_start_payload(m: Message) -> str:
    if not m.text:
        return ""
    parts = m.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@dp.message(CommandStart())
async def cmd_start(m: Message):
    ref_code = extract_start_payload(m)

    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid:
            await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except Exception:
        pass

    msg = await m.answer(
        "Добро пожаловать! Нажми кнопку ниже, чтобы открыть мини-приложение:",
        reply_markup=build_inline_kb(ref_code=ref_code),
    )
    LAST_MSG[m.from_user.id] = msg.message_id


@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    """
    Получаем заказ из MiniApp и дублируем в Telegram + отправляем на email.
    """
    try:
        data = json.loads(m.web_app_data.data)
    except Exception:
        data = {"raw": m.web_app_data.data}

    order_number = data.get("order_number", "N/A")
    total = data.get("total", 0)
    items = data.get("items", [])

    # Сообщение в телеграм
    await m.answer(
        f"📦 Новый заказ {order_number}\n"
        f"Итого: {total/100:.2f} ₽\n"
        f"Товары:\n" +
        "\n".join([f"- {i['title']} × {i['qty']} = {i['price_cents']/100:.2f} ₽" for i in items])
    )

    # Дублирование на email
    send_email(order_number, total, items)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
