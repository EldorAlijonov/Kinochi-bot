from aiogram import F, Router, types
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import ADMINS
from app.database.db import async_session_maker
from app.repositories.movie_repository import MovieRepository
from app.repositories.user_repository import UserRepository
from app.services.movie_delivery_service import MovieDeliveryService
from app.services.movie_request_context import set_pending_movie_code
from app.services.movie_service import MovieService
from app.services.subscription_gate import build_subscription_keyboard, get_subscription_gate
from app.utils.movie_code import is_movie_code

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.regexp(r"^\d{4}$"))
async def handle_movie_code_request(message: types.Message):
    if message.from_user.id in ADMINS:
        return

    raw_code = (message.text or "").strip()
    if not is_movie_code(raw_code):
        return

    try:
        async with async_session_maker() as session:
            user_repository = UserRepository(session)
            await user_repository.record_code_sent(message.from_user.id, raw_code)

        async with async_session_maker() as session:
            movie_repository = MovieRepository(session)
            movie_service = MovieService(movie_repository)
            movie = await movie_service.get_movie_by_code(raw_code)
    except SQLAlchemyError:
        logger.exception("Kino kodini qayta ishlashda database xatosi | user_id=%s", message.from_user.id)
        await message.answer("Kino kodini tekshirishda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
        return

    if not movie:
        await message.answer(
            "Kino topilmadi. Kod noto'g'ri bo'lishi, kino o'chirilgan bo'lishi yoki baza vaqtincha noaktiv holatda bo'lishi mumkin."
        )
        return

    try:
        async with async_session_maker() as session:
            unsubscribed_channels, external_links, check_error_message = await get_subscription_gate(
                bot=message.bot,
                user_id=message.from_user.id,
                session=session,
                use_cache=False,
            )
    except SQLAlchemyError:
        logger.exception("Majburiy obunalarni olishda database xatosi | user_id=%s", message.from_user.id)
        await message.answer("Obuna holatini tekshirishda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
        return

    if unsubscribed_channels:
        try:
            async with async_session_maker() as session:
                await set_pending_movie_code(session, message.from_user.id, movie.code)
        except SQLAlchemyError:
            logger.exception("Pending kino so'rovini saqlashda database xatosi | user_id=%s", message.from_user.id)
            await message.answer("Kino so'rovini saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
            return
        await message.answer(
            check_error_message
            or "Kinoni olish uchun avval majburiy obunalarga a'zo bo'ling. "
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
                user_id=message.from_user.id,
            )
    except SQLAlchemyError:
        logger.exception("Kinoni yuborishda database xatosi | user_id=%s", message.from_user.id)
        await message.answer("Kinoni yuborishda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
        return

    if not result["ok"]:
        await message.answer(result["message"])
