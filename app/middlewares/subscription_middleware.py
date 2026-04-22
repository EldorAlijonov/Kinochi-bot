import re
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import ADMINS, SUBSCRIPTION_GATE_FAIL_OPEN
from app.database.db import async_session_maker
from app.keyboards.user.subscription import subscription_check_keyboard
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _serialize_subscription(sub) -> dict:
    return {
        "id": sub.id,
        "title": sub.title,
        "subscription_type": sub.subscription_type,
        "chat_username": sub.chat_username,
        "invite_link": sub.invite_link,
    }


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        chat = getattr(event, "chat", None)

        if user is None:
            return await handler(event, data)

        if chat is not None and getattr(chat, "type", None) != "private":
            return await handler(event, data)

        if user.id in ADMINS:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and (event.data or "").startswith(
            "check_subscriptions"
        ):
            return await handler(event, data)

        if isinstance(event, Message):
            text = (event.text or "").strip()
            if text.startswith("/start") or re.fullmatch(r"\d{4}", text):
                return await handler(event, data)

        try:
            async with async_session_maker() as session:
                repository = SubscriptionRepository(session)
                service = SubscriptionService(repository)
                subscriptions = await service.get_active_subscriptions()

                if not subscriptions:
                    return await handler(event, data)

                telegram_subscriptions = [
                    sub for sub in subscriptions if sub.subscription_type != "external_link"
                ]
                external_links = [
                    sub for sub in subscriptions if sub.subscription_type == "external_link"
                ]

                check_result = await service.check_subscription_status(
                    bot=data["bot"],
                    user_id=user.id,
                    subscriptions=telegram_subscriptions,
                    use_cache=True,
                )
                unsubscribed_channels = check_result["unsubscribed_channels"] + [
                    item["subscription"]
                    for item in check_result["uncheckable_channels"]
                ]
                check_error_message = check_result["message"]
                if unsubscribed_channels:
                    user_repository = UserRepository(session)
                    await user_repository.record_subscription_block(
                        user_telegram_id=user.id,
                        blocking_subscription_id=unsubscribed_channels[0].id,
                    )
        except SQLAlchemyError:
            logger.exception("Subscription middleware database xatosi | user_id=%s", user.id)
            if SUBSCRIPTION_GATE_FAIL_OPEN:
                return await handler(event, data)
            if isinstance(event, Message):
                await event.answer("Obuna holatini tekshirishda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
                return None
            if isinstance(event, CallbackQuery):
                await event.answer("Obuna holatini tekshirib bo'lmadi. Keyinroq urinib ko'ring.", show_alert=True)
                return None
            return None

        if not unsubscribed_channels:
            return await handler(event, data)

        text = check_error_message or (
            "Botdan foydalanish uchun quyidagi kanallar yoki guruhlarga "
            "a'zo bo'ling.\n\nObuna bo'lgach, qayta tekshiring. "
            "Homiy havolalar ko'rsatma sifatida beriladi va avtomatik tekshirilmaydi."
        )

        reply_markup = subscription_check_keyboard(
            [_serialize_subscription(sub) for sub in unsubscribed_channels],
            extra_links=[_serialize_subscription(sub) for sub in external_links],
        )

        if isinstance(event, Message):
            await event.answer(text, reply_markup=reply_markup)
            return

        if isinstance(event, CallbackQuery):
            await event.message.answer(text, reply_markup=reply_markup)
            await event.answer(
                "Avval majburiy obunalarga a'zo bo'ling.",
                show_alert=True,
            )
            return

        return await handler(event, data)
