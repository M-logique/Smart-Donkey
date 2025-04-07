from logging import getLogger

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .. import settings
from .models import Base

logger = getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    logger.debug("Initializing the db...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB initialization was successfull!")
