import os, asyncio, json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")  # e.g. https://92-51-22-168.sslip.io
if not BOT_TOKEN or not WEBAPP_URL:
    raise RuntimeError("Need BOT_TOKEN and WEBAPP_URL")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
LAST_MSG = {}  # tg_user_id -> message_id (для зачистки)

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def cmd_start(m: Message):
    # разрешаем /start только для регистрации/входа — ТЗ
    # чистим старое активное сообщение (если было)
    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid: await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except: pass
    msg = await m.answer("Добро пожаловать! Откройте мини-приложение👇", reply_markup=main_menu_kb())
    LAST_MSG[m.from_user.id] = msg.message_id

@dp.message(F.web_app_data)
async def on_webapp_data(m: Message):
    # данные из Mini App через sendData
    try:
        data = json.loads(m.web_app_data.data)
    except Exception:
        data = {"raw": m.web_app_data.data}
    await m.answer(f"📦 Получено из MiniApp: <code>{json.dumps(data)}</code>", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "Назад")
async def back_to_menu(m: Message):
    # возвращаем в главное меню, скрываем старые кнопки
    try:
        mid = LAST_MSG.get(m.from_user.id)
        if mid: await bot.delete_message(chat_id=m.chat.id, message_id=mid)
    except: pass
    msg = await m.answer("Главное меню", reply_markup=main_menu_kb())
    LAST_MSG[m.from_user.id] = msg.message_id

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
