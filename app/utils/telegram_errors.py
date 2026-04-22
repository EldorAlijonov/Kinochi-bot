import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

T = TypeVar("T")


async def call_telegram_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    logger: logging.Logger,
    context: str,
    retries: int = 1,
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except TelegramRetryAfter as error:
            if attempt >= retries:
                logger.warning("%s | Telegram RetryAfter retry tugadi | retry_after=%s", context, error.retry_after)
                raise
            attempt += 1
            logger.warning("%s | Telegram RetryAfter | retry_after=%s attempt=%s", context, error.retry_after, attempt)
            await asyncio.sleep(max(1, int(error.retry_after)))


def classify_telegram_error(error: Exception) -> str:
    if isinstance(error, TelegramForbiddenError):
        return "forbidden"
    if isinstance(error, TelegramBadRequest):
        return "bad_request"
    if isinstance(error, TelegramRetryAfter):
        return "retry_after"
    return "telegram_api"
