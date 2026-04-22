import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import ADMINS
from app.database.db import async_session_maker
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
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

        try:
            async with async_session_maker() as session:
                repository = UserRepository(session)
                tracked_user = await repository.touch_user(
                    telegram_id=user.id,
                    full_name=user.full_name,
                    username=user.username,
                )
                if tracked_user.is_banned:
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
        except Exception:
            logger.exception("User aktivligini tracking qilishda xatolik")

        return await handler(event, data)
