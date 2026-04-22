import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    from app.database.models import (  # noqa: F401
        BroadcastCampaign,
        BroadcastDelivery,
        BroadcastJob,
        Movie,
        MovieBase,
        MovieCodeCounter,
        PendingMovieRequest,
        Subscription,
        User,
        UserActionLog,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized")
