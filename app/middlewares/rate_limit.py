from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import ADMINS, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
from app.services.runtime_store import RateLimitStore, rate_limit_store


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        max_requests: int = RATE_LIMIT_MAX_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
        store: RateLimitStore = rate_limit_store,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.store = store

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None or user.id in ADMINS:
            return await handler(event, data)

        is_limited = await self.store.is_limited(
            f"user:{user.id}",
            limit=self.max_requests,
            window_seconds=self.window_seconds,
        )

        if not is_limited:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(
                "So'rovlar juda tez yuborildi. Iltimos, bir necha soniya kutib qayta urinib ko'ring."
            )
            return None

        if isinstance(event, CallbackQuery):
            await event.answer(
                "Juda tez bosyapsiz. Bir necha soniya kuting.",
                show_alert=True,
            )
            return None

        if hasattr(event, "answer") and callable(getattr(event, "answer")):
            await event.answer(
                "So'rovlar juda tez yuborildi. Iltimos, bir necha soniya kutib qayta urinib ko'ring."
            )
            return None

        return None
