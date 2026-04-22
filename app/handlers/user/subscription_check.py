from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.db import async_session_maker
from app.keyboards.user.subscription import subscription_check_keyboard
from app.repositories.movie_repository import MovieRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.movie_delivery_service import MovieDeliveryService
from app.services.movie_request_context import clear_pending_movie_code, pop_pending_movie_code
from app.services.subscription_service import SubscriptionService
from app.utils.callbacks import parse_callback_parts

router = Router()
logger = logging.getLogger(__name__)


def _serialize_subscription(sub) -> dict:
    return {
        "id": sub.id,
        "title": sub.title,
        "subscription_type": sub.subscription_type,
        "chat_username": sub.chat_username,
        "invite_link": sub.invite_link,
    }


@router.callback_query(F.data.startswith("check_subscriptions"))
async def check_subscriptions(callback: CallbackQuery):
    user_id = callback.from_user.id
    callback_parts = parse_callback_parts(callback.data, min_parts=1) or []
    requested_movie_code = None
    if len(callback_parts) == 3 and callback_parts[1] == "movie":
        requested_movie_code = callback_parts[2]

    try:
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)

            subscriptions = await service.get_active_subscriptions()
            telegram_subscriptions = [
                sub for sub in subscriptions if sub.subscription_type != "external_link"
            ]
            external_links = [
                sub for sub in subscriptions if sub.subscription_type == "external_link"
            ]

            check_result = await service.check_subscription_status(
                bot=callback.bot,
                user_id=user_id,
                subscriptions=telegram_subscriptions,
                use_cache=not bool(requested_movie_code),
            )
            unsubscribed_channels = check_result["unsubscribed_channels"] + [
                item["subscription"] for item in check_result["uncheckable_channels"]
            ]
            check_error_message = check_result["message"]
            blocking_subscription_id = (
                unsubscribed_channels[0].id if unsubscribed_channels else None
            )
            user_repository = UserRepository(session)
            await user_repository.record_subscription_check(
                user_telegram_id=user_id,
                is_success=not bool(unsubscribed_channels),
                blocking_subscription_id=blocking_subscription_id,
            )
    except SQLAlchemyError:
        logger.exception("Obuna tekshiruvini qayta ishlashda database xatosi | user_id=%s", user_id)
        await callback.answer(
            "Obuna tekshiruvida vaqtinchalik xatolik yuz berdi. Keyinroq urinib ko'ring.",
            show_alert=True,
        )
        return

    if not unsubscribed_channels:
        if requested_movie_code:
            try:
                async with async_session_maker() as session:
                    await clear_pending_movie_code(session, user_id)
            except SQLAlchemyError:
                logger.exception("Pending kino so'rovini tozalashda database xatosi | user_id=%s", user_id)
        else:
            try:
                async with async_session_maker() as session:
                    requested_movie_code = await pop_pending_movie_code(session, user_id)
            except SQLAlchemyError:
                logger.exception("Pending kino so'rovini olishda database xatosi | user_id=%s", user_id)
                await callback.answer(
                    "Kino so'rovini tiklashda xatolik yuz berdi. Kodni qayta yuboring.",
                    show_alert=True,
                )
                return

        movie_code = requested_movie_code
        if movie_code:
            try:
                async with async_session_maker() as session:
                    delivery_service = MovieDeliveryService(MovieRepository(session))
                    result = await delivery_service.send_movie_by_code(
                        bot=callback.bot,
                        chat_id=callback.message.chat.id,
                        raw_code=movie_code,
                        user_id=user_id,
                    )
            except SQLAlchemyError:
                logger.exception("Obunadan keyin kinoni yuborishda database xatosi | user_id=%s", user_id)
                await callback.answer(
                    "Kinoni yuborishda vaqtinchalik xatolik yuz berdi. Kodni qayta yuboring.",
                    show_alert=True,
                )
                return

            if result["ok"]:
                try:
                    await callback.message.delete()
                except TelegramBadRequest:
                    pass
            else:
                try:
                    await callback.message.edit_text(result["message"])
                except TelegramBadRequest as error:
                    if "message is not modified" not in str(error):
                        raise

            await callback.answer()
            return

        try:
            await callback.message.edit_text(
                "Barcha Telegram obunalar bajarilgan. Kino kodini yuboring."
            )
        except TelegramBadRequest as error:
            if "message is not modified" not in str(error):
                raise

        await callback.answer()
        return

    text = check_error_message or (
        "Siz hali quyidagi obunalarga ulanmagansiz.\n\n"
        "Iltimos, Telegram obunalarga a'zo bo'lib qayta tekshiring. "
        "Homiy havolalar ko'rsatma sifatida beriladi va avtomatik tekshirilmaydi."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=subscription_check_keyboard(
                [_serialize_subscription(sub) for sub in unsubscribed_channels],
                extra_links=[_serialize_subscription(sub) for sub in external_links],
                check_callback_data=callback.data or "check_subscriptions",
            ),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise

    await callback.answer()
