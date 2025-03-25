import logging
from asyncio import run as asyncio_run
from io import BytesIO

from g4f import Provider
from g4f.client import AsyncClient
from PIL import Image
from sqlalchemy.future import select
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message as TelebotMessage

from error_handler import ErrorHandler
from smart_donkey import settings
from smart_donkey._defaults import DEFAULT_CONFIG_VALUES
from smart_donkey.checkers import check_access, cooldown
from smart_donkey.crud.access import grant_access
from smart_donkey.crud.config import get_config, register_config
from smart_donkey.crud.messages import add_message, get_messages
from smart_donkey.crud.users import get_user, register_user
from smart_donkey.db import *
from utils import format_messages
from telebot import types 


logger = logging.getLogger(__name__)


bot = AsyncTeleBot(token=settings.TOKEN, parse_mode="Markdown", validate_token=True, 
    exception_handler=ErrorHandler                 
)


@bot.message_handler(commands=["start"])
async def start_command(message: TelebotMessage):
    async with SessionLocal() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            welcome_msg = (
                "👋 Welcome to Smart Donkey Bot!\n\n"
                "Type /help to see what I can do for you!"
            )
            await register_user(session, message.from_user.id)
            await register_config(session, message.chat.id, **DEFAULT_CONFIG_VALUES)
            await bot.reply_to(message, welcome_msg)
        else:
            normal_msg = "Welcome back! How can I assist you today?"
            await bot.reply_to(message, normal_msg)


@bot.message_handler(commands=["ask"])
@check_access()
@cooldown(3)
async def ask_command(message: TelebotMessage):
    await bot.send_chat_action(message.chat.id, 'typing')
    async with SessionLocal() as session:
        messages = await get_messages(
            session, message.chat.id, message.from_user.id, 30
        )
        config = await get_config(session, message.chat.id)

        dict_message = {
            "role": "user",
            "content": message.text or "No content in the message.",
        }

        file_hash = None
        fetched = False
        image = None

        if message.photo:
            file_hash = message.photo[-1].file_id
        elif message.reply_to_message and message.reply_to_message.photo:
            file_hash = message.reply_to_message.photo[-1].file_id

        if not file_hash:
            result = await session.execute(
                select(Message.file_hash)
                .where(
                    Message.file_hash != None,
                    Message.chat_id == message.chat.id,
                    Message.author_id == message.from_user.id,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            file_hash = result.scalar()
            logger.debug("Fetched file hash from database: %s", file_hash)
            fetched = True

        if file_hash:
            file = await bot.get_file(file_hash)
            downloaded_file = await bot.download_file(file.file_path)

            bytes_io = BytesIO(downloaded_file)
            image = Image.open(bytes_io)

        provider = getattr(Provider, config.provider)
        client = AsyncClient(provider)


        # TODO: Send message if couldn't reply

        dict_messages = format_messages(messages, instruction=config.instructions) + [dict_message]
        logger.debug("Generating response in %d, Messages: %s", message.chat.id, str(dict_messages))
        logger.debug("file hash: %s", file_hash)

        try:
            response = await client.chat.completions.create(
                model=config.model,
                messages=dict_messages,
                image=image,
            )
            response_message = response.choices[0].message.content
        except Exception as err:
            await bot.reply_to(message, f"❗️ There was an error: {err}")
            return
        

        await bot.reply_to(message, response_message)

        # Add message to the database
        await add_message(
            session,
            dict_message.get("content"),
            message.id,
            message.from_user.id,
            message.chat.id,
            "user",
            file_hash if not fetched else None,
        )
        await add_message(
            session,
            response_message,
            message.id,
            message.from_user.id,
            message.chat.id,
            "assistant",
            file_hash if not fetched else None,
        )

@bot.message_handler(commands=["config"])
async def config_command(message: TelebotMessage):

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn = types.InlineKeyboardButton
    user_id = message.from_user.id

    markup.add(
        btn("⚙️ Model", callback_data=f"conf_model:{user_id}"),
        btn("🌐 Provider", callback_data=f"conf_provider:{user_id}"),
        btn("📝 Instruction", callback_data=f"conf_instruction:{user_id}"),
        btn("📡 Streaming", callback_data=f"conf_streaming:{user_id}"),
        btn("💾 Save", callback_data=f"conf_save:{user_id}")
    )

    await bot.reply_to(message, "💠 **Select what you want to change:**", reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("conf_"))
async def handle_config_callback(call: types.CallbackQuery):
    data, user_id = call.data.split(":")
    chat_id = call.message.chat.id
    message_id = call.message.id

    if str(call.from_user.id) != user_id:
        await bot.answer_callback_query(call.id, "⛔ You are not allowed to use this!", show_alert=True)
        return
    
    call_instance_id = f"_config_of_{chat_id}_{user_id}_{message_id}"
    config = getattr(bot, call_instance_id)

    if not config:
        config = dict()

    setattr(bot, call_instance_id, config)

    # await bot.answer_callback_query(call.id, "✅ Setting applied!")
    # await bot.send_message(call.message.chat.id, f"🔧 You selected `{data[5:]}`.", parse_mode="Markdown")

async def main():
    await init_db()
    # async with SessionLocal() as session:
    #     await grant_access(session, 5520073297, 5520073297, AccessType.GLOBAL)
    # async with SessionLocal() as session:
    #     await register_config(session, 5520073297, **DEFAULT_CONFIG_VALUES)
    await bot.polling()


asyncio_run(main())
