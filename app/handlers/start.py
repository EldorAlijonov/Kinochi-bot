from aiogram import Router, types
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import CommandObject, CommandStart
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import ADMINS
from app.database.db import async_session_maker
from app.keyboards.admin.reply import admin_menu
from app.keyboards.user.subscription import subscription_check_keyboard
from app.repositories.movie_repository import MovieRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.movie_delivery_service import MovieDeliveryService
from app.services.movie_request_context import set_pending_movie_code
from app.services.movie_service import MovieService
from app.services.subscription_gate import build_subscription_keyboard, get_subscription_gate
from app.services.subscription_service import SubscriptionService
from app.utils.text import safe_html
from app.utils.movie_code import is_movie_code

router = Router()
logger = logging.getLogger(__name__)
START_ERROR_MESSAGE = (
    "So'rovni qayta ishlashda vaqtinchalik xatolik yuz berdi. "
    "Iltimos, keyinroq qayta urinib ko'ring."
)


def _extract_referrer_id(payload: str) -> int | None:
    if not payload.startswith("ref_"):
        return None

    raw_referrer_id = payload.removeprefix("ref_")
    if not raw_referrer_id.isdigit():
        return None

    return int(raw_referrer_id)


def _serialize_subscription(sub) -> dict:
    return {
        "id": sub.id,
        "title": sub.title,
        "subscription_type": sub.subscription_type,
        "chat_username": sub.chat_username,
        "invite_link": sub.invite_link,
    }


@router.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    full_name = safe_html(message.from_user.full_name)
    movie_code = (command.args or "").strip()
    referrer_id = _extract_referrer_id(movie_code) if movie_code else None

    if user_id in ADMINS:
        await message.answer(
            f"Admin panelga xush kelibsiz, <b>{full_name}</b>.",
            reply_markup=admin_menu,
        )
        return

    try:
        async with async_session_maker() as session:
            user_repository = UserRepository(session)
            await user_repository.upsert_user(
                telegram_id=user_id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                referred_by=referrer_id,
                start_payload=movie_code or None,
            )
            await user_repository.record_start(user_id, payload=movie_code or None)
    except SQLAlchemyError:
        logger.exception("Start user trackingda database xatosi | user_id=%s payload=%s", user_id, movie_code)
        await message.answer(START_ERROR_MESSAGE)
        return

    if movie_code:
        if not is_movie_code(movie_code):
            if referrer_id is None:
                await message.answer(
                    "<b>Kino topilmadi. Kod noto'g'ri.</b>"
                )
                return
            movie_code = ""

        if movie_code:
            try:
                async with async_session_maker() as session:
                    user_repository = UserRepository(session)
                    await user_repository.record_share_start(user_id, movie_code)

                async with async_session_maker() as session:
                    movie_repository = MovieRepository(session)
                    movie_service = MovieService(movie_repository)
                    movie = await movie_service.get_movie_by_code(movie_code)
            except SQLAlchemyError:
                logger.exception("Start deep link kinoni olishda database xatosi | user_id=%s code=%s", user_id, movie_code)
                await message.answer(START_ERROR_MESSAGE)
                return

            if not movie:
                await message.answer(
                    "<b>Kino topilmadi. Kod noto'g'ri.</b>"
                )
                return

            try:
                async with async_session_maker() as session:
                    unsubscribed_channels, external_links, check_error_message = await get_subscription_gate(
                        bot=message.bot,
                        user_id=user_id,
                        session=session,
                        use_cache=False,
                    )
            except SQLAlchemyError:
                logger.exception("Start obuna gate database xatosi | user_id=%s code=%s", user_id, movie_code)
                await message.answer(START_ERROR_MESSAGE)
                return
            except TelegramForbiddenError:
                logger.exception("Start obuna gate Telegram forbidden | user_id=%s code=%s", user_id, movie_code)
                await message.answer("Bot obuna holatini tekshira olmadi. Iltimos, keyinroq qayta urinib ko'ring.")
                return
            except TelegramAPIError:
                logger.exception("Start obuna gate Telegram xatosi | user_id=%s code=%s", user_id, movie_code)
                await message.answer("Obuna holatini tekshirib bo'lmadi. Iltimos, keyinroq qayta urinib ko'ring.")
                return

            if unsubscribed_channels:
                try:
                    async with async_session_maker() as session:
                        await set_pending_movie_code(session, user_id, movie.code)
                except SQLAlchemyError:
                    logger.exception("Start pending kino so'rovini saqlashda database xatosi | user_id=%s code=%s", user_id, movie.code)
                    await message.answer(START_ERROR_MESSAGE)
                    return
                await message.answer(
                    check_error_message
                    or "Kinoni olish uchun avval obunalarga a'zo bo'ling. "
                    "Homiy havolalar alohida ko'rsatiladi, ular Telegram orqali avtomatik tekshirilmaydi.",
                    reply_markup=build_subscription_keyboard(
                        unsubscribed_channels,
                        external_links,
                        check_callback_data=f"check_subscriptions:movie:{movie.code}",
                    ),
                )
                return

            try:
                async with async_session_maker() as session:
                    delivery_service = MovieDeliveryService(MovieRepository(session))
                    result = await delivery_service.send_movie_by_code(
                        bot=message.bot,
                        chat_id=message.chat.id,
                        raw_code=movie.code,
                        user_id=user_id,
                    )
            except SQLAlchemyError:
                logger.exception("Start kinoni yuborishda database xatosi | user_id=%s code=%s", user_id, movie.code)
                await message.answer(START_ERROR_MESSAGE)
                return
            except TelegramForbiddenError:
                logger.exception("Start kinoni yuborishda Telegram forbidden | user_id=%s code=%s", user_id, movie.code)
                await message.answer("Bot sizga kino yubora olmadi. Iltimos, botni blokdan chiqaring va qayta urinib ko'ring.")
                return
            except TelegramAPIError:
                logger.exception("Start kinoni yuborishda Telegram xatosi | user_id=%s code=%s", user_id, movie.code)
                await message.answer("Kinoni yuborib bo'lmadi. Iltimos, keyinroq qayta urinib ko'ring.")
                return

            if not result["ok"]:
                await message.answer(result["message"])
            return

    try:
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            subscriptions = await service.get_active_subscriptions()
    except SQLAlchemyError:
        logger.exception("Start obunalar ro'yxatini olishda database xatosi | user_id=%s", user_id)
        await message.answer(START_ERROR_MESSAGE)
        return

    if not subscriptions:
        await message.answer(f"Assalomu alaykum, <b>{full_name}</b>.")
        return

    telegram_subscriptions = [
        sub for sub in subscriptions if sub.subscription_type != "external_link"
    ]
    external_links = [
        sub for sub in subscriptions if sub.subscription_type == "external_link"
    ]

    await message.answer(
        f"Assalomu alaykum, <b>{full_name}</b>.\n\n"
        "Botdan foydalanish uchun quyidagi obunalarga a'zo bo'ling.",
        reply_markup=subscription_check_keyboard(
            [_serialize_subscription(sub) for sub in telegram_subscriptions],
            extra_links=[_serialize_subscription(sub) for sub in external_links],
        ),
    )
