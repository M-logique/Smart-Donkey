from logging import getLogger
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from utils import stringify_attributes
from ..db import *

logger = getLogger(__name__)


async def register_chat(session: AsyncSession, chat_id: int) -> Chat:
    logger.debug("Registering chat: %s", chat_id)

    new_chat = Chat(chat_id=chat_id)
    session.add(new_chat)

    await session.commit()
    await session.refresh(new_chat)

    logger.debug("Chat registered successfully: %s", chat_id)
    return new_chat


async def delete_chat(session: AsyncSession, chat_id: int) -> bool:
    logger.debug("Attempting to delete chat: %s", chat_id)

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat = result.scalars().first()

    if chat:
        await session.delete(chat)
        await session.commit()
        logger.debug("Chat deleted successfully: %s", chat_id)
        return True

    logger.debug("Chat not found: %s", chat_id)
    return False


async def get_chat(session: AsyncSession, chat_id: int) -> Chat:

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))

    chat = result.scalars().first()

    if not chat:
        logger.debug("Chat with id: %d not found", chat_id)
    else:
        logger.debug("Chat found: %s", stringify_attributes(chat))

    return chat
