import time
from functools import wraps
from logging import getLogger

from telebot.types import CallbackQuery
from telebot.types import Message as TelebotMessage

from smart_donkey import settings
from smart_donkey._defaults import DEFAULT_CONFIG_VALUES
from smart_donkey.crud.chats import get_chat, register_chat
from smart_donkey.crud.config import get_config, register_config
from smart_donkey.crud.users import get_user, register_user
from smart_donkey.db import SessionLocal

logger = getLogger(__name__)

user_cooldowns = {}


def check_config():
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: TelebotMessage, *args, **kwargs):
            msg = message
            if isinstance(message, CallbackQuery):
                msg = message.message
            async with SessionLocal() as session:
                config = await get_config(session, msg.chat.id, message.from_user.id)

                if not config:
                    await register_config(session, msg.chat.id,user_id=message.from_user.id, **DEFAULT_CONFIG_VALUES)

            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator


def register_missings():
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: TelebotMessage, *args, **kwargs):
            async with SessionLocal() as session:
                user = await get_user(session, message.from_user.id)
                chat = await get_chat(session, message.chat.id)
                if not user:
                    await register_user(session, message.from_user.id)
                if not chat:
                    await register_chat(session, message.chat.id)
            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator


def check_owner(bot):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: TelebotMessage, *args, **kwargs):
            if not message.from_user.id in settings.OWNERS:
                return await bot.reply_to(message, "نه")
            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator


def cooldown(seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            current_time = time.time()

            if user_id in user_cooldowns:
                last_request_time = user_cooldowns[user_id]
                if current_time - last_request_time < seconds:
                    # await message.reply(f"⌛️ Please wait {seconds - (current_time - last_request_time):.1f} seconds before making another request.")
                    return

            user_cooldowns[user_id] = current_time
            return await func(message, *args, **kwargs)

        return wrapper

    return decorator
