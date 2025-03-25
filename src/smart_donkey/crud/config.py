from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from smart_donkey.db.models import Config

logger = getLogger(__name__)


async def register_config(
    session: AsyncSession, chat_id: int, model: str, provider: str, streaming: bool, instructions: str
) -> Config:
    logger.debug(
        "Registering config for chat: %s, model: %s, provider: %s",
        chat_id,
        model,
        provider,
    )

    new_config = Config(
        chat_id=chat_id, model=model, provider=provider, streaming=streaming, instructions=instructions
    )
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
    session: AsyncSession, chat_id: int, model: str, provider: str
) -> bool:
    logger.debug(
        "Updating config for chat: %s, model: %s, provider: %s",
        chat_id,
        model,
        provider,
    )

    result = await session.execute(select(Config).where(Config.chat_id == chat_id))
    config = result.scalars().first()

    if config:
        config.model = model
        config.provider = provider

        await session.commit()
        logger.debug("Config updated successfully for chat: %s", chat_id)
        return True

    logger.debug("Config not found for chat: %s, creating new config", chat_id)
    await register_config(session, chat_id, model, provider)
    return False
