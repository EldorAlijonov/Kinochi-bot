import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import ADMINS
from app.database.db import async_session_maker
from app.repositories.user_repository import UserRepository
from app.services.runtime_store import CacheStore, cache_store

logger = logging.getLogger(__name__)
USER_TRACKING_THROTTLE_SECONDS = 300


class UserTrackingMiddleware(BaseMiddleware):
    def __init__(
        self,
        store: CacheStore = cache_store,
        throttle_seconds: int = USER_TRACKING_THROTTLE_SECONDS,
    ) -> None:
        self.store = store
        self.throttle_seconds = throttle_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        chat = getattr(event, "chat", None)
        if isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None

        if user is None or user.id in ADMINS:
            return await handler(event, data)

        if chat is not None and getattr(chat, "type", None) != "private":
            return await handler(event, data)

        cache_key = f"user_tracking:{user.id}"
        try:
            async with async_session_maker() as session:
                repository = UserRepository(session)
                should_touch = await self.store.get(cache_key) != "1"
                if should_touch:
                    tracked_user = await repository.touch_user(
                        telegram_id=user.id,
                        full_name=user.full_name,
                        username=user.username,
                    )
                    is_banned = tracked_user.is_banned
                else:
                    is_banned = await repository.get_is_banned(user.id)
                    if is_banned is None:
                        tracked_user = await repository.touch_user(
                            telegram_id=user.id,
                            full_name=user.full_name,
                            username=user.username,
                        )
                        is_banned = tracked_user.is_banned

                if is_banned:
                    if isinstance(event, Message):
                        await event.answer(
                            "Siz botdan foydalanishdan cheklangansiz. Admin bilan bog'laning."
                        )
                        return None

                    if isinstance(event, CallbackQuery):
                        await event.answer(
                            "Siz botdan foydalanishdan cheklangansiz.",
                            show_alert=True,
                        )
                        return None

                if should_touch:
                    await self.store.set(cache_key, "1", self.throttle_seconds)
        except Exception:
            logger.exception("User aktivligini tracking qilishda xatolik")

        return await handler(event, data)
