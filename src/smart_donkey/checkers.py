from functools import wraps
from logging import getLogger

from telebot.types import Message as TelebotMessage

from smart_donkey import settings
from smart_donkey._defaults import DEFAULT_CONFIG_VALUES
from smart_donkey.crud.access import has_access
from smart_donkey.crud.config import get_config, register_config
from smart_donkey.db import SessionLocal
import time

logger = getLogger(__name__)

user_cooldowns = {}

def check_access_and_config():
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: TelebotMessage, *args, **kwargs):
            async with SessionLocal() as session:
                accessed = await has_access(
                    session, message.chat.id, message.from_user.id
                )
                if not accessed:
                    logger.warning("User not accessed: %d", message.from_user.id)
                    return
                config = await get_config(session, message.chat.id)

                if not config:
                    await register_config(session, message.chat.id, **DEFAULT_CONFIG_VALUES)


            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator



def check_owner():
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: TelebotMessage, *args, **kwargs):
            if not message.from_user.id in settings.OWNERS:
                return
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
                    await message.reply(f"⌛️ Please wait {seconds - (current_time - last_request_time):.1f} seconds before making another request.")
                    return

            user_cooldowns[user_id] = current_time
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator

