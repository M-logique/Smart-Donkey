from logging import getLogger
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from utils import stringify_attributes

from ..db import *

logger = getLogger(__name__)


async def register_user(session: AsyncSession, user_id: int) -> User:
    new_user = User(user_id=user_id)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    logger.debug("User created: %s", stringify_attributes(new_user))
    return new_user


async def delete_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()

    if user:
        logger.debug("User deleted: %s", stringify_attributes(user))
        session.delete(user)
        await session.commit()
    else:
        logger.debug("User not found for deletion: user_id %d", user_id)


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()

    if user:
        logger.debug("User retrieved: %s", stringify_attributes(user))
    else:
        logger.debug("User not found: user_id %d", user_id)

    return user
