import ast
import asyncio
import json
import logging
from asyncio import gather
from asyncio import run as asyncio_run
from io import BytesIO
import os

from aiohttp import ClientSession
from g4f import Provider
from g4f.client import AsyncClient
from PIL import Image
from sqlalchemy import func, text
from sqlalchemy.future import select
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message as TelebotMessage

from error_handler import ErrorHandler
from gpt_assistant import settings
from gpt_assistant._defaults import DEFAULT_CONFIG_VALUES
from gpt_assistant.checkers import (check_config, check_owner, cooldown,
                                   register_missings)
from gpt_assistant.crud.config import get_config, register_config, update_config
from gpt_assistant.crud.messages import add_message, get_messages
from gpt_assistant.crud.users import get_user, register_user
from gpt_assistant.db import *
from gpt_assistant.db.models import ImageGeneration
from utils import extract_text, format_messages, generate_config_message, no_need_to_think

logger = logging.getLogger(__name__)


bot = AsyncTeleBot(
    token=settings.TOKEN,
    parse_mode="Markdown",
    validate_token=True,
    exception_handler=ErrorHandler,
)


@bot.message_handler(commands=["start"])
@register_missings()
@check_config()
async def start_command(message: TelebotMessage):
    async with SessionLocal() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            welcome_msg = (
                "👋 Welcome to Smart Donkey Bot!\n\n"
                "Type /help to see what I can do for you!"
            )
            await register_user(session, message.from_user.id)
            await register_config(
                session,
                message.chat.id,
                user_id=message.from_user.id,
                **DEFAULT_CONFIG_VALUES,
            )
            await bot.reply_to(message, welcome_msg)
        else:
            normal_msg = "Welcome back! How can I assist you today?"
            await bot.reply_to(message, normal_msg)


MAX_MESSAGE_LENGTH = 4096  # Telegram's max message length


@bot.message_handler(commands=["ask"])
@register_missings()
@check_config()
@cooldown(3)
async def ask_command(message: TelebotMessage):
    await bot.send_chat_action(message.chat.id, "typing")
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id, message.from_user.id)

        messages = await get_messages(
            session,
            message.chat.id,
            message.from_user.id,
            config.language_model.lower(),
            30,
        )
        config = await get_config(session, message.chat.id, message.from_user.id)

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

        dict_messages = format_messages(messages, instruction=config.instructions) + [
            dict_message
        ]
        logger.debug(
            "Generating response in %d, Messages: %s",
            message.chat.id,
            str(dict_messages),
        )
        logger.debug("file hash: %s", file_hash)

        try:
            response = await client.chat.completions.create(
                model=config.language_model,
                messages=dict_messages,
                image=image,
            )
            response_message = response.choices[0].message.content
            if config.language_model.lower() == "deepseek-r1":
                response_message = no_need_to_think(response_message)
        except Exception as err:
            await bot.reply_to(message, f"❗️ There was an error: {err}")
            return

        for chunk in split_text(response_message, MAX_MESSAGE_LENGTH):
            await bot.reply_to(message, chunk)

        await add_message(
            session,
            content=dict_message.get("content"),
            message_id=message.id,
            author_id=message.from_user.id,
            chat_id=message.chat.id,
            role="user",
            file_hash=file_hash if not fetched else None,
            model=config.language_model.lower(),
        )
        await add_message(
            session,
            content=response_message,
            message_id=message.id,
            author_id=message.from_user.id,
            chat_id=message.chat.id,
            role="assistant",
            file_hash=file_hash if not fetched else None,
            model=config.language_model.lower(),
        )


def split_text(text, max_length):
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


@bot.message_handler(commands=["imagine"])
@register_missings()
@check_config()
@cooldown(7)
async def imagine_command(message: TelebotMessage):
    text = extract_text(message.text)
    if not text:
        await bot.reply_to(
            message,
            "🚧 Correct usage:\n  -> /imagine **text**\n\n💡 -> You can reply to an image to use it in image generations",
        )
        return
    await bot.send_chat_action(message.chat.id, "upload_photo")

    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id, message.from_user.id)

        image_model = config.image_model

    if not image_model:
        await bot.reply_to(
            message, "❗️ Your current provider does not support image generations!"
        )
        return

    client = AsyncClient(
        image_provider=getattr(Provider, config.provider),
    )

    file_hash = None
    image = None

    if message.photo:
        file_hash = message.photo[-1].file_id
    elif message.reply_to_message and message.reply_to_message.photo:
        file_hash = message.reply_to_message.photo[-1].file_id

    if file_hash:
        file = await bot.get_file(file_hash)
        downloaded_file = await bot.download_file(file.file_path)

        bytes_io = BytesIO(downloaded_file)
        image = Image.open(bytes_io)

    response = await client.images.generate(
        prompt=text, model=config.image_model, image=image, response_format="url"
    )

    image_urls = [data.url for data in response.data]

    async def fetch_image(url: str):
        async with ClientSession() as session:
            async with session.get(url) as resp:
                return BytesIO(await resp.read())

    bytes_io_list = await gather(*(fetch_image(url) for url in image_urls))

    medias = [
        types.InputMediaPhoto(media=bytes_io, caption=f"💡 Prompt: _{text}_")
        for bytes_io in bytes_io_list
    ]

    messages = await bot.send_media_group(message.chat.id, media=medias)

    file_hashes = [msg.photo[-1].file_id for msg in messages if msg.photo]

    async with SessionLocal() as session:
        image_generation = ImageGeneration(
            prompt=text,
            message_id=message.id,
            author_id=message.from_user.id,
            chat_id=message.chat.id,
            input_file_hash=file_hash,
            output_file_hashes=json.dumps(file_hashes),
        )

        session.add(image_generation)
        await session.commit()


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
@register_missings()
@check_config()
async def config_command(message: TelebotMessage):
    await bot.send_chat_action(message.chat.id, "typing")
    markup = get_config_markup(message.from_user.id)
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id, message.from_user.id)

    await bot.reply_to(
        message,
        generate_config_message(config),
        reply_markup=markup,
        parse_mode="Markdown",
    )


async def show_provider_selector(message: TelebotMessage, user_id: int):
    markup = types.InlineKeyboardMarkup(row_width=3)

    all_providers = [
        getattr(Provider, p)
        for p in dir(Provider)
        if isinstance(getattr(Provider, p), type) and p != "Local"
    ]

    free_providers = [
        provider
        for provider in all_providers
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
        types.InlineKeyboardButton(
            provider.__name__,
            callback_data=f"conf_provider_{provider.__name__}:{user_id}",
        )
        for provider in free_providers
    ]
    buttons.append(
        types.InlineKeyboardButton("↬ Back", callback_data=f"conf_back:{user_id}")
    )

    markup.add(*buttons)

    await bot.edit_message_text(
        "🌐 **Please select a provider:**",
        message.chat.id,
        message.id,
        reply_markup=markup,
    )


async def show_language_model_selector(message: TelebotMessage, user_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id, int(user_id))

        provider = config.provider

    provider_cls = getattr(Provider, provider)

    language_models = provider_cls.models

    buttons = [
        types.InlineKeyboardButton(model, callback_data=f"conf_lm_{model}:{user_id}")
        for model in language_models
    ]

    buttons.append(
        types.InlineKeyboardButton("↬ Back", callback_data=f"conf_back:{user_id}")
    )

    markup.add(*buttons)

    await bot.edit_message_text(
        "💬 Select a language model: ", message.chat.id, message.id, reply_markup=markup
    )


async def show_image_model_selector(message: TelebotMessage, user_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    async with SessionLocal() as session:
        config = await get_config(session, message.chat.id, int(user_id))

        provider = config.provider

    provider_cls = getattr(Provider, provider)

    image_models = provider_cls.image_models

    buttons = [
        types.InlineKeyboardButton(model, callback_data=f"conf_lm_{model}:{user_id}")
        for model in image_models
    ]

    buttons.append(
        types.InlineKeyboardButton("↬ Back", callback_data=f"conf_back:{user_id}")
    )

    markup.add(*buttons)

    text = "🖼️ Select an image model: "

    if len(buttons) == 1:
        text = "❗️ Your current provider has no image models"

    await bot.edit_message_text(text, message.chat.id, message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("conf_"))
@check_config()
async def handle_config_callback(call: types.CallbackQuery):
    data, user_id = call.data.split(":")
    chat_id = call.message.chat.id
    message_id = call.message.id

    data = data[5:]

    if call.from_user.id != int(user_id):
        await bot.answer_callback_query(
            call.id, "⛔ You are not allowed to use this!", show_alert=True
        )
        return

    async with SessionLocal() as session:
        conf = await get_config(session, chat_id, int(user_id))
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
        config["streaming"] = not conf.streaming
        state = "Enabled" if config["streaming"] else "Disabled"
        await bot.answer_callback_query(call.id, f"📡 Streaming is now {state}")

    if data.startswith("provider_"):
        provider_name = data[len("provider_") :]
        config["provider"] = provider_name
        provider_cls = getattr(Provider, provider_name)
        config["language_model"] = provider_cls.default_model
        config["image_model"] = getattr(provider_cls, "default_image_model", None)

    if data.startswith("lm_"):
        lm_name = data[len("lm_") :]
        config["language_model"] = lm_name

    async with SessionLocal() as session:
        await update_config(session, chat_id, user_id=call.from_user.id, **config)

    await bot.edit_message_text(
        generate_config_message(conf), chat_id, message_id, reply_markup=get_config_markup(user_id)
    )


@bot.message_handler(commands=["instruction"])
@register_missings()
@check_config()
@cooldown(3)
async def set_instructions(message: TelebotMessage):
    text = extract_text(message.text)

    if not text:
        await bot.reply_to(message, "🚧 Correct usage:\n  -> /instruction **text**")
        return

    async with SessionLocal() as session:
        await update_config(
            session, message.chat.id, user_id=message.from_user.id, instruction=text
        )

    await bot.reply_to(message, "✏️ instructions updated successfully!")


@bot.message_handler(commands="clear_history")
@register_missings()
@check_config()
@cooldown(3)
async def clear_history_command(message: TelebotMessage):
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count(Message._id)).where(
                Message.author_id == message.from_user.id
            )
        )

    message_count = result.scalar()

    if message_count == 0:
        await bot.reply_to(message, "You don't have any messages.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)

    buttons = (
        types.InlineKeyboardButton(
            "✅ Yes", callback_data=f"ch_confirm_yes:{message.from_user.id}"
        ),
        types.InlineKeyboardButton(
            "❌ No", callback_data=f"ch_confirm_no:{message.from_user.id}"
        ),
    )

    markup.add(*buttons)
    s = "" if message_count == 1 else "s"
    await bot.reply_to(
        message,
        f"❓️Are you sure you want to clear {message_count} message{s}?",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_confirm_"))
async def clear_yes_no_handler(call: types.CallbackQuery):
    data, user_id = call.data.split(":")

    user_id = int(user_id)
    data = data[len("ch_confirm_") :]

    if user_id != call.from_user.id:
        await bot.answer_callback_query(
            call.id, "⛔ You are not allowed to use this!", show_alert=True
        )
        return

    if data == "yes":
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text="⌛️ Started purging your history...",
            reply_markup=None,
        )
        async with SessionLocal() as session:
            await session.execute(
                text("DELETE FROM messages WHERE author_id = :user_id"),
                {"user_id": user_id},
            )
            await session.commit()
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text="✅ Your history has been cleaned successfully",
        )
    elif data == "no":
        await bot.edit_message_text(
            "❌ Action canceled. ",
            reply_markup=None,
            chat_id=call.message.chat.id,
            message_id=call.message.id,
        )

def insert_returns(body):
    # insert return stmt if the last expression is an expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)

@bot.message_handler(commands=["e", "exec"])
@check_owner(bot)
async def exec_command(message: TelebotMessage):

    try:
        code = extract_text(message.text)
        fn_name = "_eval_expr"
        cmd = "\n".join(f"    {line}" for line in code.strip("` ").splitlines())
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        insert_returns(parsed.body[0].body)

        env = {
            "client": bot,
            "bot": bot,
            "message": message,
            "imp": __import__,
            "asyncio": asyncio,
            "os": os,
        }

        exec(compile(parsed, filename="<ast>", mode="exec"), env)
        result = await eval(f"{fn_name}()", env)
    except Exception as err:
        await bot.reply_to(message, f"Execution failed: {err}")
        return

    if result is None:
        await bot.reply_to(message, "✅ Code executed successfully.")
    else:
        result_str = str(result)
        await bot.reply_to(message, result_str[:4096]) 




async def main():
    await init_db()
    await bot.polling()


asyncio_run(main())
