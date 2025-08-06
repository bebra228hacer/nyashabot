import asyncio
import datetime
import json
import logging
import logging.handlers
import os

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Filter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from openrouters import send_request_to_openrouter # Импорт конкретной функции

import telegramify_markdown 
from telegramify_markdown import customize

import user_db  
from user_db import User


load_dotenv()
TG_TOKEN = os.environ.get("TG_TOKEN")
LLM_TOKEN = os.environ.get("LLM_TOKEN")
DEBUG = bool(int(os.environ.get("DEBUG")))
DEBUG_CHAT = int(os.environ.get("DEBUG_CHAT"))
DATABASE_NAME = os.environ.get("DATABASE_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
DELAYED_REMINDERS_HOURS = int(os.environ.get("DELAYED_REMINDERS_HOURS"))
DELAYED_REMINDERS_MINUTES = int(os.environ.get("DELAYED_REMINDERS_MINUTES"))
TIMEZONE_OFFSET = int(os.environ.get("TIMEZONE_OFFSET"))
FROM_TIME = int(os.environ.get("FROM_TIME"))
TO_TIME = int(os.environ.get("TO_TIME"))
with open("prompts.json", encoding="utf-8") as ofile:
    PROMPTS = json.load(ofile)
    DEFAULT_PROMPT = PROMPTS["DEFAULT_PROMPT"]
    REMINDER_PROMPT = PROMPTS["REMINDER_PROMPT"]
with open("messages.json", encoding="utf-8") as ofile:
    MESSAGES = json.load(ofile)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
fh = logging.handlers.RotatingFileHandler(
    "debug.log", maxBytes=1024 * 1024, backupCount=5, encoding="utf8"
)
fh.setLevel(logging.DEBUG)  #
formatter_console = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter_console)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)

customize.strict_markdown = True
customize.cite_expandable = True


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


async def keep_typing(chat_id):
    """
    Периодически показывает статус "печатает..." для чат-бота.
    """
    for i in range(10):
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(3)


async def f_debug(message_chat_id, message_id):
    if DEBUG:
        await bot.forward_message(
            chat_id=DEBUG_CHAT, from_chat_id=message_chat_id, message_id=message_id
        )


@dp.message(F.chat.id == DEBUG_CHAT)
async def test(message):
    pass


@dp.message(
    OldMessage()
)  # чтобы не отвечал на сообщения которым больше минуты с момента обработки
async def spam(message):
    pass


@dp.message(UserNotInDB())
async def registration(message):
    user = message.from_user
    if user and user.username != None:
        username = user.username
    else:
        username = "Not_of_registration"
    user = User(int(message.chat.id), username)
    await user.save_for_db()
    builder = ReplyKeyboardBuilder()

    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=builder.as_markup()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_start"], reply_markup=ReplyKeyboardRemove()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_help"], reply_markup=ReplyKeyboardRemove()
    )
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(Command("forget"))
async def cmd_forget(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_forget"], reply_markup=ReplyKeyboardRemove()
    )
    user = User(message.chat.id)
    await user.get_from_db()
    user.remind_of_yourself = "0"
    user.prompt = []
    await user.update_in_db()

    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(Command("reminder"))
async def cmd_reminder(message: types.Message):
    sent_msg = await message.answer(
        MESSAGES["msg_reminder"], reply_markup=ReplyKeyboardRemove()
    )
    user = User(message.chat.id)
    await user.get_from_db()
    user.remind_of_yourself = "0"
    await user.update_in_db()
    await f_debug(message.chat.id, message.message_id)
    await f_debug(message.chat.id, sent_msg.message_id)


@dp.message(F.text)
async def LLC_request(message: types.Message):

    logger.info(f"USER{message.chat.id}TOLLC:{message.text}")
    await f_debug(message.chat.id, message.message_id)

    typing_task = asyncio.create_task(keep_typing(message.chat.id))
    user = User(message.chat.id)
    await user.get_from_db()
    await user.update_prompt("user", message.text)
    prompt_for_request = user.prompt.copy()
    prompt_for_request.append({"role": "system", "content": DEFAULT_PROMPT})
    try:
        llc_msg = await send_request_to_openrouter(prompt_for_request)
    except Exception as e:
        await bot.send_message(
            DEBUG_CHAT, f"LLC{message.chat.id} - Критическая ошибка: {e}"
        )
    if llc_msg is None or llc_msg.strip() == "":
        await bot.send_message(
            DEBUG_CHAT, f"LLC{message.chat.id} - пустой ответ от llc"
        )
        return
    await user.update_prompt("assistant", llc_msg)

    logger.debug(f"LLC_RAWOUTPUT{message.chat.id}:{llc_msg}")

    converted = telegramify_markdown.markdownify(
        llc_msg,
        max_line_length=None,
        normalize_whitespace=False,
    )

    try:
        generated_message = await message.answer(
            converted,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except TelegramForbiddenError:
            typing_task.cancel()
            user.remind_of_yourself = 0
            await user.update_in_db()
            await bot.send_message(DEBUG_CHAT, f"USER{id} заблокировал чатбота")
            typing_task.cancel()
            return
    except Exception as e:
        generated_message = await bot.send_message(
            DEBUG_CHAT, f"LLC{message.chat.id} - {e}"
        )
        logger.error(f"LLC{message.chat.id} - {e}")
        generated_message = await message.answer(
            converted,
        )
    typing_task.cancel()
    user.remind_of_yourself = await user_db.time_after(
        DELAYED_REMINDERS_HOURS,
        DELAYED_REMINDERS_MINUTES,
        TIMEZONE_OFFSET,
        FROM_TIME,
        TO_TIME,
    )
    await user.update_in_db()
    await f_debug(message.chat.id, generated_message.message_id)
    logger.info(f"LLC{message.chat.id} - {generated_message.text}")


@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(MESSAGES["unknown_message"])


async def reminder():
    for id in await user_db.get_past_dates():
        user = User(id)
        await user.get_from_db()
        if user.prompt:
            if len(user.prompt) >= 2:
                if user.prompt[-2]["role"] == "assistant":
                    if user.prompt[-1]["role"] == "assistant":
                        user.prompt.pop()
        prompt_for_request = user.prompt.copy()
        prompt_for_request.append({"role": "system", "content": REMINDER_PROMPT})
        prompt_for_request.insert(0, ({"role": "system", "content": DEFAULT_PROMPT}))
        typing_task = asyncio.create_task(keep_typing(id))
        try:
            llc_msg = await send_request_to_openrouter(prompt_for_request)
        except Exception as e:
            await bot.send_message(DEBUG_CHAT, f"LLC{id} - Критическая ошибка: {e}")
        if llc_msg is None or llc_msg.strip() == "":
            await bot.send_message(DEBUG_CHAT, f"LLC{id} - пустой ответ от llc")
            return
        await user.update_prompt("assistant", llc_msg)

        logger.debug(f"LLC_RAWOUTPUT{id}:{llc_msg}")

        converted = telegramify_markdown.markdownify(
            llc_msg,
            max_line_length=None,
            normalize_whitespace=False,
        )

        try:
            generated_message = await bot.send_message(
                chat_id=id,
                text=converted,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except TelegramForbiddenError:
            typing_task.cancel()
            user.remind_of_yourself = 0
            await user.update_in_db()
            await bot.send_message(DEBUG_CHAT, f"USER{id} заблокировал чатбота")
            typing_task.cancel()
            return
        except Exception as e:
            await bot.send_message(DEBUG_CHAT, f"LLC{id} - {e}")
            logger.error(f"LLC{id} - {e}")
            generated_message = await bot.send_message(
                chat_id=id,
                text=converted,
            )
        typing_task.cancel()
        user.remind_of_yourself = await user_db.time_after(
            DELAYED_REMINDERS_HOURS,
            DELAYED_REMINDERS_MINUTES,
            TIMEZONE_OFFSET,
            FROM_TIME,
            TO_TIME,
        )
        await user.update_in_db()
        await f_debug(id, generated_message.message_id)
        logger.info(f"LLC{id}REMINDER - {generated_message.text}")


async def main():
    try:
        print(await user_db.check_db())
        print("Основная часть запущена")
        print("Отладка:\n")
        polling_task = asyncio.create_task(dp.start_polling(bot))
        while True:
            await reminder()
            await asyncio.sleep(30)
    except Exception as e:
        print(f"Ошибка: {e}")
        await bot.send_message(DEBUG_CHAT, f"Произошла ошибка:'{e}'")
        logger.debug(f"CRITICAL_ERROR:{e}")


if __name__ == "__main__":
    asyncio.run(main())
