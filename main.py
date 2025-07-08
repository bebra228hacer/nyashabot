import json
import user_db
from user_db import User
import re
import os
import asyncio
import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.filters import Filter
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from openrouters import send_request_to_openrouter
from aiogram import Bot, Dispatcher, types
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove

load_dotenv()
TG_TOKEN = os.environ.get("TG_TOKEN")
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(int(os.environ.get("DEBUG")))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
DELAYED_REMINDERS = int(os.environ.get("DELAYED_REMINDERS"))
with open("prompts.json", encoding="utf-8") as ofile:
    PROMPTS = json.load(ofile)
    DEFAULT_PROMPT = PROMPTS["DEFAULT_PROMPT"]
    REMINDER_PROMPT = PROMPTS["REMINDER_PROMPT"]
with open("messages.json", encoding="utf-8") as ofile:
    MESSAGES = json.load(ofile)

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()


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
            return int(user.is_admin) >= 1
        else:
            return False

class OldMessage(Filter):
    async def __call__(self, message: types.Message) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)  
        message_time = message.date.replace(tzinfo=datetime.timezone.utc) 
        time_difference = now - message_time
        return time_difference >= datetime.timedelta(minutes=1)






async def console_log(owner, text, entered_text="", cut_back = True, state = True):
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    entered_text = entered_text.replace('\n', ' ')
    entered_text = entered_text.replace('\r', ' ')
    entered_text = re.sub(r'\s+', ' ', entered_text).strip()
    debug_string = f'[{datetime.datetime.now().strftime("%H.%M.%S")}|{owner}] >> {text}'
    if entered_text and cut_back and len(entered_text)>=50:
        entered_text = entered_text[:50]
        debug_string = f'{debug_string}:"{entered_text}..."'
    elif entered_text and cut_back:
        debug_string = f'{debug_string}:"{entered_text}..."'
    print(debug_string)

async def f_debug(message_chat_id, message_id):
    if DEBUG:
        await bot.forward_message(
            chat_id=DEBUG_CHAT, from_chat_id=message_chat_id, message_id=message_id
        )







@dp.message(F.chat.id == DEBUG_CHAT)
async def test(message):
    # sent_msg = await message.answer("ГОВОРЯЩАЯ АДМИНИСТРАЦИЯ")
    pass

@dp.message(OldMessage())   #чтобы не отвечал на сообщения которым больше минуты с момента обработки
async def spam(message):
    #print("пуньк")
    pass

@dp.message(UserNotInDB())
async def registration(message):
    user = message.from_user
    if user and user.username!=None:
        username = user.username
    else:
        username = "Not_of_registration"
    user = User(int(message.chat.id), username)
    await user.save_for_db()
    builder = ReplyKeyboardBuilder()
    #builder.button(text=MESSAGES["btn_main_menu_sub"])
    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=builder.as_markup()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)

@dp.message(Command("start"))
async def cmd_answer(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=ReplyKeyboardRemove()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)

@dp.message(Command("help"))
async def cmd_answer(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_help"], reply_markup=ReplyKeyboardRemove()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)

@dp.message(Command("forget"))
async def cmd_answer(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_forget"], reply_markup=ReplyKeyboardRemove()
    )
    user = User(message.chat.id)
    await user.get_from_db()
    user.remind_of_yourself = "2077-06-15 22:03:51"
    user.prompt = []
    await user.update_in_db()
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)

@dp.message(F.text)
async def LLC_request(message: types.Message):
    
    await console_log(f"USER{message.chat.id}", "LLC_request", message.text)
    await f_debug(message.chat.id, message.message_id)
    
    generating_message = await bot.send_message(
        message.chat.id, "Текст генерируется..."
    )
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user = User(message.chat.id)
    await user.get_from_db()
    await user.update_prompt("user", message.text)
    prompt_for_request = user.prompt.copy()
    prompt_for_request.append({"role": "system", "content": DEFAULT_PROMPT})
    llc_msg = await send_request_to_openrouter(prompt_for_request)
    await user.update_prompt("assistant", llc_msg)
    await console_log(f"send_request_to_openrouter_raw_output", llc_msg, state = False)
    llc_msg = llc_msg.replace("**","*")
    llc_msg = llc_msg.replace("***","*")
    llc_msg = llc_msg.replace("****","*")
    llc_msg = llc_msg.replace("#","")
    pattern = '[' + re.escape(r'[]()>\#+\-={}.!') + ']'
    llc_msg = re.sub(pattern, r'\\\g<0>', llc_msg) 
    await console_log(f"send_request_to_openrouter_output", llc_msg, state=False)
    try:
        generating_message = await bot.edit_message_text(
            llc_msg,
            chat_id=message.chat.id,
            message_id=generating_message.message_id,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except TelegramBadRequest as e:
        pattern = '[' + re.escape(r'_*~`|') + ']'
        llc_msg = re.sub(pattern, r'\\\g<0>', llc_msg) 
        try:
            generating_message = await bot.edit_message_text(
                llc_msg,
                chat_id=message.chat.id,
                message_id=generating_message.message_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except TelegramBadRequest as e:
            generating_message = await bot.edit_message_text(
                llc_msg,
                chat_id=message.chat.id,
                message_id=generating_message.message_id,
            )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        generating_message = await bot.edit_message_text(
            "Произошла ошибка при генерации текста.",
            chat_id=message.chat.id,
            message_id=generating_message.message_id,
        )
        return
    user.remind_of_yourself = await user_db.time_after(DELAYED_REMINDERS)
    await user.update_in_db()
    await console_log(f"ASSIST", "LLC_request", generating_message.text)
    await f_debug(message.chat.id, generating_message.message_id)

@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(MESSAGES["unknown_message"])








async def reminder():
    for id in await user_db.get_past_dates():
        user = User(id)
        await user.get_from_db()
        prompt_for_request = user.prompt.copy()
        prompt_for_request.append({"role": "system", "content": REMINDER_PROMPT})
        llc_msg = await send_request_to_openrouter(prompt_for_request)
        
        try:
            sent_msg = await bot.send_message(
                chat_id=id, text=llc_msg, parse_mode=ParseMode.MARKDOWN_V2
            )
        except TelegramBadRequest as e:
            llc_msg = re.sub(r"(\*\*|\_\_|\~\~)", r"\\\g<1>", llc_msg)
            llc_msg = re.sub(r"([\[\]()>\#\+\=\-\.!\`\|\{\}])", r"\\\g<1>", llc_msg)
            try:
                sent_msg = await bot.send_message(
                    chat_id=id, text=llc_msg, parse_mode=ParseMode.MARKDOWN_V2
                )
            except TelegramBadRequest as e:
                sent_msg = await bot.send_message(
                    chat_id=id, text=llc_msg, parse_mode=ParseMode.MARKDOWN_V2
                )
        await user.update_prompt("assistant", sent_msg.text)
        user.remind_of_yourself = "2077-06-15 22:03:51"
        await user.update_in_db()
        
        await console_log(f"ASSIST", "reminder", llc_msg)
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
