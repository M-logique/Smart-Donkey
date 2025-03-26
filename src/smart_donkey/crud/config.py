from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from smart_donkey.db.models import Config

logger = getLogger(__name__)


async def register_config(
    session: AsyncSession, chat_id: int, **kwargs
) -> Config:


    new_config = Config(
        chat_id=chat_id, **kwargs)
    session.add(new_config)

    await session.commit()
    await session.refresh(new_config)

    logger.debug("Config registered successfully for chat: %s", chat_id)
    return new_config


async def delete_config(session: AsyncSession, chat_id: int) -> bool:
    logger.debug("Attempting to delete config for chat: %s", chat_id)

    result = await session.execute(select(Config).where(Config.chat_id == chat_id))
    config = result.scalars().first()

    if config:
        await session.delete(config)
        await session.commit()
        logger.debug("Config deleted successfully for chat: %s", chat_id)
        return True

    logger.debug("Config not found for chat: %s", chat_id)
    return False


async def get_config(session: AsyncSession, chat_id: int) -> Config | None:
    logger.debug("Fetching config for chat: %s", chat_id)

    result = await session.execute(select(Config).where(Config.chat_id == chat_id))
    config = result.scalars().first()

    if config:
        logger.debug("Config found for chat: %s", chat_id)
    else:
        logger.debug("No config found for chat: %s", chat_id)

    return config


async def update_config(
    session: AsyncSession, chat_id: int, **kwargs,
) -> bool:

    result = await session.execute(select(Config).where(Config.chat_id == chat_id))
    config = result.scalars().first()

    if config:
        for k, v in kwargs.items():
            setattr(config, k, v)

        await session.commit()
        logger.debug("Config updated successfully for chat: %s", chat_id)
        return True
    
    await register_config(session, chat_id, **kwargs)
