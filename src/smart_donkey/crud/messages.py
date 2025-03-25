from logging import getLogger
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from utils import stringify_attributes
from ..db import *

logger = getLogger(__name__)


async def add_message(
    session: AsyncSession,
    content: str,
    message_id: int,
    author_id: int,
    chat_id: int,
    role: str,
    file_hash: Optional[str] = None,
) -> Message:
    new_message = Message(
        content=content,
        author_id=author_id,
        chat_id=chat_id,
        file_hash=file_hash,
        message_id=message_id,
        role=role,
    )
    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)
    logger.debug("Message added: %s", stringify_attributes(new_message))
    return new_message


async def remove_message(session: AsyncSession, message_id: int) -> bool:
    result = await session.execute(
        select(Message).filter(Message.message_id == message_id)
    )
    message = result.scalars().first()

    if message:
        logger.debug("Message found, deleting: %s", stringify_attributes(message))
        await session.delete(message)
        await session.commit()
        logger.debug("Message deleted: %s", stringify_attributes(message))
        return True
    else:
        logger.debug("Message with _id %d not found", message_id)
        return False


async def get_message(session: AsyncSession, message_id: int) -> Optional[Message]:
    result = await session.execute(
        select(Message).filter(Message.message_id == message_id)
    )
    message = result.scalars().first()

    if message:
        logger.debug("Message found: %s", stringify_attributes(message))
    else:
        logger.debug("Message with _id %d not found", message_id)

    return message


async def get_messages(
    session: AsyncSession, chat_id: int, user_id: int, limit: Optional[int] = 30
) -> List[Message]:
    result = await session.execute(
        select(Message)
        .filter(
            and_(
                Message.chat_id == chat_id,
                Message.author_id == user_id
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    if messages:
        logger.debug(
            "Found %d messages for chat_id %d and user_id: %d",
            len(messages),
            chat_id,
            user_id,
        )
    else:
        logger.debug("No messages found for chat_id %d", chat_id)

    return messages