import aiosqlite
import json

import user_db
from user_db import User


import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.filters import Filter
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from openrouters import chat_stream, send_request_to_openrouter

with open("messages.json", encoding='utf-8') as ofile:
    MESSAGES = json.load(ofile)
load_dotenv()
TG_TOKEN = os.environ.get("TG_TOKEN")
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(int(os.environ.get("DEBUG")))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME =  os.environ.get("TABLE_NAME")
with open("prompts.json", encoding='utf-8') as ofile:
    DEFAULT_PROMPT = json.load(ofile)
    DEFAULT_PROMPT = DEFAULT_PROMPT['DEFAULT_PROMPT']


bot = Bot(token = TG_TOKEN)
dp = Dispatcher()



async def f_debug(message_chat_id, message_id):
    if DEBUG:
        await bot.forward_message(chat_id=DEBUG_CHAT, from_chat_id = message_chat_id, message_id=message_id)


class UserNotInDB(Filter):
    async def __call__(self, message: types.Message) -> bool:
        user_id = message.chat.id
        return not await user_db.user_exists(user_id)

class UserHaveSubLevel(Filter):
    def __init__(self, required_sub_lvl: int):
        self.required_sub_lvl = required_sub_lvl

    async def __call__(self, message: types.Message) -> bool:
        user = User(message.chat.id)  
        await user.get_from_db()
        if user:
            return user.sub_lvl >= self.required_sub_lvl 
        else:
            return False  



@dp.message(F.chat.id == DEBUG_CHAT)
async def test(message):
    #sent_msg = await message.answer("ГОВОРЯЩАЯ АДМИНИСТРАЦИЯ")
    pass

@dp.message(UserNotInDB())
async def test(message):
    user = message.from_user
    if user and user.username:
        username = user.username
    user = User(int(message.chat.id), username)
    await user.save_for_db()
    builder = ReplyKeyboardBuilder()
    builder.button(text=MESSAGES["btn_main_menu_sub"])
    sent_msg = await message.answer(MESSAGES["msg_start"], reply_markup=builder.as_markup())
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)
    
@dp.message(Command("start"))
async def cmd_answer(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text=MESSAGES["btn_main_menu_sub"])
    if UserHaveSubLevel(1):
        builder.button(text=MESSAGES["btn_main_menu_profile"])
    sent_msg = await message.answer(MESSAGES["msg_start"], reply_markup=builder.as_markup())
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)

@dp.message(F.text.lower() == "анкета" and UserHaveSubLevel(1))
async def main_profile_handler(message: types.Message):
    await message.answer("мяу")

@dp.message()
async def LLC_request(message: types.Message):
    user_db = User(message.chat.id)
    await user_db.get_from_db()
    prompt_for_request = user_db.prompt.copy()
    prompt_for_request.insert(0, {"role": "user", "content": DEFAULT_PROMPT})
    print(prompt_for_request)
    sent_msg = await message.answer(send_request_to_openrouter(prompt_for_request))
    await user_db.update_prompt("user", message.text)

    await user_db.update_prompt("assistant", sent_msg.text)
    await user_db.update_in_db()
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


async def main():
    print(await user_db.check_db()) 
    print("Основная часть запущена")
    print("Отладка:")
    print()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())