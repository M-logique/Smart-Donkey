from logging import getLogger

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from gpt_assistant.db.models import Config

logger = getLogger(__name__)


async def register_config(session: AsyncSession, chat_id: int, **kwargs) -> Config:

    new_config = Config(chat_id=chat_id, **kwargs)
    session.add(new_config)

    await session.commit()
    await session.refresh(new_config)

    logger.debug("Config registered successfully for chat: %s", chat_id)
    return new_config


async def get_config(
    session: AsyncSession, chat_id: int, user_id: int
) -> Config | None:
    logger.debug("Fetching config for chat: %s", chat_id)

    result = await session.execute(
        select(Config).where(and_(Config.chat_id == chat_id, Config.user_id == user_id))
    )
    config = result.scalars().first()

    if config:
        logger.debug("Config found for chat: %s", chat_id)
    else:
        logger.debug("No config found for chat: %s", chat_id)

    return config


async def update_config(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    **kwargs,
) -> bool:

    result = await session.execute(select(Config).where(and_(Config.chat_id == chat_id, Config.user_id == user_id)))
    config = result.scalars().first()

    if config:
        for k, v in kwargs.items():
            setattr(config, k, v)

        await session.commit()
        logger.debug("Config updated successfully for chat: %s", chat_id)
        return True

    await register_config(session, chat_id, **kwargs)
