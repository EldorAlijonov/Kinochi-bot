import logging

from sqlalchemy import text

from app.core.config import settings
from app.database.db import engine
from app.services.runtime_store import cache_store

logger = logging.getLogger(__name__)


async def validate_runtime_dependencies() -> None:
    if not settings.is_production:
        return

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    if not await cache_store.ping():
        raise RuntimeError("Redis runtime store ping muvaffaqiyatsiz yakunlandi.")

    logger.info("Production runtime dependency check muvaffaqiyatli yakunlandi")
