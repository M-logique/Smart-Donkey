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
from smart_donkey.checkers import check_access_and_config, cooldown
from smart_donkey.crud.config import get_config, register_config, update_config
from smart_donkey.crud.messages import add_message, get_messages
from smart_donkey.crud.users import get_user, register_user
from smart_donkey.db import *
from utils import extract_text, format_messages
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
@check_access_and_config()
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
            "content": extract_text(message.text) or "No content in the message.",
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

def get_config_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn = types.InlineKeyboardButton

    markup.add(
        btn("🌐 Provider", callback_data=f"conf_provider:{user_id}"),
        btn("💬 Language Model", callback_data=f"conf_lm:{user_id}"),
        btn("🖼️ Image Model", callback_data=f"conf_im:{user_id}"),
        btn("📡 Streaming", callback_data=f"conf_streaming:{user_id}"),
    )

    return markup

@bot.message_handler(commands=["config"])
async def config_command(message: TelebotMessage):
    await bot.send_chat_action(message.chat.id, 'typing')
    markup = get_config_markup(message.from_user.id)
    await bot.reply_to(message, "💠 **Select what you want to change:**", reply_markup=markup, parse_mode="Markdown")


async def show_provider_selector(message: TelebotMessage, user_id: int):
    markup = types.InlineKeyboardMarkup(row_width=3)

    all_providers = [
        getattr(Provider, p) for p in dir(Provider)
        if isinstance(getattr(Provider, p), type) and p != "Local"
    ]

    free_providers = [
        provider for provider in all_providers
        if hasattr(provider, "supports_system_message") 
        and hasattr(provider, "supports_message_history") 
        and hasattr(provider, "needs_auth")
        and hasattr(provider, "default_model")
        and provider.supports_system_message
        and provider.supports_message_history
        and not provider.needs_auth
        and provider.default_model
    ]

    buttons = [
        types.InlineKeyboardButton(provider.__name__, callback_data=f"conf_provider_{provider.__name__}:{user_id}")
        for provider in free_providers
    ]
    buttons.append(
        types.InlineKeyboardButton(
            "↬ Back", 
            callback_data=f"conf_back:{user_id}"
        )
    )

    markup.add(*buttons)

    await bot.edit_message_text("🌐 **Please select a provider:**", message.chat.id, message.id, reply_markup=markup)

async def show_language_model_selector(message: TelebotMessage, user_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id)

        provider = config.provider

    provider_cls = getattr(Provider, provider)

    language_models = provider_cls.models

    buttons = [
        types.InlineKeyboardButton(model, callback_data=f"conf_lm_{model}:{user_id}")
        for model in language_models
    ]

    buttons.append(
        types.InlineKeyboardButton(
            "↬ Back", 
            callback_data=f"conf_back:{user_id}"
        )
    )

    markup.add(*buttons)

    await bot.edit_message_text("💬 Select a language model: ", message.chat.id, message.id, reply_markup=markup)

async def show_image_model_selector(message: TelebotMessage, user_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id)

        provider = config.provider

    provider_cls = getattr(Provider, provider)

    image_models = provider_cls.image_models

    buttons = [
        types.InlineKeyboardButton(model, callback_data=f"conf_lm_{model}:{user_id}")
        for model in image_models
    ]

    buttons.append(
        types.InlineKeyboardButton(
            "↬ Back", 
            callback_data=f"conf_back:{user_id}"
        )
    )

    markup.add(*buttons)

    text = "🖼️ Select an image model: "

    if len(buttons) == 1:
        text = "❗️ Your current provider has no image models"

    await bot.edit_message_text(text, message.chat.id, message.id, reply_markup=markup)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("conf_"))
@check_access_and_config()
async def handle_config_callback(call: types.CallbackQuery):
    data, user_id = call.data.split(":")
    chat_id = call.message.chat.id
    message_id = call.message.id

    data = data[5:]

    if call.from_user.id != int(user_id):
        await bot.answer_callback_query(call.id, "⛔ You are not allowed to use this!", show_alert=True)
        return
    
    config = dict()

    if data == "provider":
        await show_provider_selector(call.message, user_id)
        return
    
    if data == "lm":
        await show_language_model_selector(call.message, user_id)
        return
    
    if data == "im":
        await show_image_model_selector(call.message, user_id)
        return
    
    if data == "streaming":
        async with SessionLocal() as session:
            config = await get_config(session, chat_id)
            config["streaming"] = not config.streaming
            state = "Enabled" if config["streaming"] else "Disabled"
            await bot.answer_callback_query(call.id, f"📡 Streaming is now {state}")



    if data.startswith("provider_"):
        provider_name = data[len("provider_"):]
        config["provider"] = provider_name
        provider_cls = getattr(Provider, provider_name)
        config["language_model"] = provider_cls.default_model
        config["image_model"] = getattr(provider_cls, "default_image_model", None)
    
    if data.startswith("lm_"):
        lm_name = data[len("lm_"):]
        config["language_model"] = lm_name
    
    
    text = "💠 **Select what you want to change:**"
    async with SessionLocal() as session:
        await update_config(session, chat_id, **config)

    await bot.edit_message_text(text, chat_id, message_id, reply_markup=get_config_markup(user_id))

@bot.message_handler(commands=["instruction"])
@check_access_and_config()
@cooldown(3)
async def set_instructions(message: TelebotMessage):
    text = extract_text(message.text)

    if not text:
        await bot.reply_to(message, "🚧 Correct usage:\n  -> /instruction **text**")
        return
    
    async with SessionLocal() as session:
        await update_config(session, message.chat.id, instruction=text)

    await bot.reply_to(message, "✏️ instructions updated successfully!")
    
async def main():
    await init_db()
    await bot.polling()


asyncio_run(main())
