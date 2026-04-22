import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import SQLAlchemyError

T = TypeVar("T")


async def safe_db_call(
    operation: Callable[[], Awaitable[T]],
    *,
    logger: logging.Logger,
    context: str,
) -> T | None:
    try:
        return await operation()
    except SQLAlchemyError:
        logger.exception("%s | database xatosi", context)
        return None
