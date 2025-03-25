from logging import getLogger
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from utils import stringify_attributes
from ..db import *

logger = getLogger(__name__)


async def has_access(session: AsyncSession, chat_id: int, user_id: int) -> bool:
    logger.debug("Checking access for user_id: %d in chat_id: %d", user_id, chat_id)

    result = await session.execute(
        select(Accessed).filter(
            or_(
                Accessed.access_type == AccessType.ALL,
                and_(
                    Accessed.user_id == user_id,
                    Accessed.access_type == AccessType.GLOBAL
                ),
                and_(
                    Accessed.chat_id == chat_id,
                    Accessed.access_type == AccessType.CHAT_ONLY
                ),
                and_(
                    Accessed.chat_id == chat_id,
                    Accessed.user_id == user_id,
                    Accessed.access_type == AccessType.USER_IN_CHAT
                )
            )
        )
    )
    access_record = result.scalars().first()

    if access_record:
        logger.debug("User_id: %d has access to chat_id: %d", user_id, chat_id)
    else:
        logger.debug(
            "User_id: %d does not have access to chat_id: %d", user_id, chat_id
        )

    return access_record is not None


async def grant_access(
    session: AsyncSession,
    chat_id: Optional[int],
    user_id: Optional[int],
    access_type: AccessType,
) -> Accessed:
    logger.debug(
        "Granting access. Chat_id: %s, User_id: %s, Access_type: %s",
        chat_id,
        user_id,
        access_type,
    )

    kwargs = {"access_type": access_type}

    if chat_id is not None:
        kwargs["chat_id"] = chat_id
    if user_id is not None:
        kwargs["user_id"] = user_id

    new_access = Accessed(**kwargs)
    session.add(new_access)
    await session.commit()
    await session.refresh(new_access)

    logger.debug(
        "Access granted. New access record: %s",
        stringify_attributes(new_access),
    )

    return new_access


async def remove_access(
    session: AsyncSession, chat_id: Optional[int], user_id: Optional[int]
):
    logger.debug("Removing access. Chat_id: %s, User_id: %s", chat_id, user_id)

    kwargs = {}
    if chat_id is not None:
        kwargs["chat_id"] = chat_id
    if user_id is not None:
        kwargs["user_id"] = user_id

    result = await session.execute(select(Accessed).filter_by(**kwargs))
    access = result.scalars().first()

    if access:
        logger.debug("Access found: %s", stringify_attributes(access))
        await session.delete(access)
        await session.commit()
        logger.debug("Access removed successfully.")
        return True
    else:
        logger.debug("No access found for chat_id: %s, user_id: %s", chat_id, user_id)
        return False
