import aiosqlite
import json

import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

with open("messages.json", encoding='utf-8') as ofile:
    MESSAGES = json.load(ofile)
load_dotenv()
TG_TOKEN = os.environ.get("TG_TOKEN")
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(os.environ.get("DEBUG"))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")


bot = Bot(token = TG_TOKEN)
dp = Dispatcher()

async def check_db():
    """Проверяет и создает базу данных и таблицу, если они не существуют."""
    try:  # Добавляем обработку исключений
        async with aiosqlite.connect(DATABASE_NAME) as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY, 
                        name TEXT NOT NULL,
                        sub_lvl INTEGER,
                        is_admin INTEGER
                    )
                """
                )
            await db.commit()
        return "База данных в порядке"
    except aiosqlite.Error as e:
        return f"Ошибка при проверке/создании базы данных: {e}"


async def f_debug(message_chat_id, message_id):
    if DEBUG:
        await bot.forward_message(chat_id=DEBUG_CHAT, from_chat_id = message_chat_id, message_id=message_id)
    

@dp.message(Command("start"))
async def cmd_answer(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text=MESSAGES["btn_main_menu_sub"])
    builder.button(text=MESSAGES["btn_main_menu_profile"])
    sent_msg = await message.answer(MESSAGES["msg_start"], reply_markup=builder.as_markup())
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(F.text.lower())
async def main_sub_handler(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="гойда", callback_data="Nothing")
    await message.answer("Some text here", reply_markup=builder.as_markup())
@dp.message(F.text.lower() == "анкета")
async def main_profile_handler(message: types.Message):
    await message.answer()


@dp.message()
async def echo_handler(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="гойда", callback_data="Nothing")
    await message.answer("Some text here", reply_markup=builder.as_markup())
@dp.message(F.text.lower() == "анкета")
async def echo_handler(message: types.Message):
    await message.answer()


async def main():
    """Основная функция, которая запускает проверку БД и другие задачи."""
    db_status = await check_db()
    print(db_status) 
    print("Start success")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())