import json
import user_db
from user_db import User
import re
import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.filters import Filter
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from openrouters import send_request_to_openrouter



with open("messages.json", encoding="utf-8") as ofile:
    MESSAGES = json.load(ofile)
load_dotenv()
TG_TOKEN = os.environ.get("TG_TOKEN")
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(int(os.environ.get("DEBUG")))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
DELAYED_REMINDERS = os.environ.get("DELAYED_REMINDERS")
with open("prompts.json", encoding="utf-8") as ofile:
    PROMPTS = json.load(ofile)
    DEFAULT_PROMPT = PROMPTS["DEFAULT_PROMPT"]
    REMINDER_PROMPT = PROMPTS["REMINDER_PROMPT"]


bot = Bot(token=TG_TOKEN)
dp = Dispatcher()





async def f_debug(message_chat_id, message_id):
    if DEBUG:
        await bot.forward_message(
            chat_id=DEBUG_CHAT, from_chat_id=message_chat_id, message_id=message_id
        )


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

class UserIsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        user = User(message.chat.id)
        await user.get_from_db()
        if user:
            return user.sub_lvl >= self.required_sub_lvl
        else:
            return False



@dp.message(F.chat.id == DEBUG_CHAT)
async def test(message):
    # sent_msg = await message.answer("ГОВОРЯЩАЯ АДМИНИСТРАЦИЯ")
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
    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=builder.as_markup()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(Command("start"))
async def cmd_answer(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text=MESSAGES["btn_main_menu_sub"])
    if UserHaveSubLevel(1):
        builder.button(text=MESSAGES["btn_main_menu_profile"])
    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=builder.as_markup()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(F.text.lower() == "анкета" and UserHaveSubLevel(1))
async def main_profile_handler(message: types.Message):
    await bot.send_message(message.chat.id, "Не нужно", parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(F.text.lower() == "мяу")
async def main_profile_handler(message: types.Message):
    await bot.send_message(message.chat.id, "**мяу**", parse_mode=ParseMode.MARKDOWN_V2)



@dp.message()
async def LLC_request(message: types.Message):
    generating_message = await bot.send_message(message.chat.id, "Текст генерируется...")
    user = User(message.chat.id)
    await user.get_from_db()
    await user.update_prompt("user", message.text)
    prompt_for_request = user.prompt.copy()
    prompt_for_request.append({"role": "system", "content": DEFAULT_PROMPT})
    llc_msg = await send_request_to_openrouter(prompt_for_request)

    try:
        await bot.edit_message_text(llc_msg, chat_id=message.chat.id, message_id=generating_message.message_id, parse_mode=ParseMode.MARKDOWN_V2)
    except TelegramBadRequest as e:
        llc_msg = re.sub(r"(\*\*|\_\_|\~\~)", r"\\\g<1>", llc_msg)
        llc_msg = re.sub(r"([\[\]()>\#\+\=\-\.!\`\|\{\}])", r"\\\g<1>", llc_msg)
        try:
            await bot.edit_message_text(llc_msg, chat_id=message.chat.id, message_id=generating_message.message_id, parse_mode=ParseMode.MARKDOWN_V2)
        except TelegramBadRequest as e:
            await bot.edit_message_text(llc_msg, chat_id=message.chat.id, message_id=generating_message.message_id)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  
        await bot.edit_message_text("Произошла ошибка при генерации текста.", chat_id=message.chat.id, message_id=generating_message.message_id)
        return

    await user.update_prompt("assistant", generating_message.text)
    user.remind_of_yourself = await user_db.time_after(DELAYED_REMINDERS)
    await user.update_in_db()
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, generating_message.message_id)


async def reminder():
    for id in await user_db.get_past_dates():
        user = User(id)
        await user.get_from_db()
        prompt_for_request = user.prompt.copy()
        prompt_for_request.append({"role": "system", "content": REMINDER_PROMPT})
        llc_msg = await send_request_to_openrouter(prompt_for_request)
        try:
            sent_msg = await bot.send_message(
            chat_id=id, text=llc_msg,
            parse_mode=ParseMode.MARKDOWN_V2)
        except TelegramBadRequest as e:
            llc_msg = re.sub(r"(\*\*|\_\_|\~\~)", r"\\\g<1>", llc_msg) 
            llc_msg = re.sub(r"([\[\]()>\#\+\=\-\.!\`\|\{\}])", r"\\\g<1>", llc_msg)
            try:
                sent_msg = await bot.send_message(
                chat_id=id, text=llc_msg,
                parse_mode=ParseMode.MARKDOWN_V2)
            except TelegramBadRequest as e:
                sent_msg = await bot.send_message(
                chat_id=id, text=llc_msg,
                parse_mode=ParseMode.MARKDOWN_V2)
        await user.update_prompt("assistant", sent_msg.text)
        user.remind_of_yourself = "2077-06-15 22:03:51"
        await user.update_in_db()
        await f_debug(id, sent_msg.message_id)



async def main():
    print(await user_db.check_db())
    print("Основная часть запущена")
    print("Отладка:\n")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    while True:
        await reminder()
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())