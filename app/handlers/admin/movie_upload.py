import math
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.errors import (
    MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE,
    is_movie_title_schema_mismatch,
)
from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import cancel_keyboard
from app.keyboards.admin.movie_base_inline import movie_base_selection_keyboard
from app.keyboards.admin.movies import MOVIES_UPLOAD_BUTTON, movies_menu
from app.repositories.movie_base_repository import MovieBaseRepository
from app.repositories.movie_repository import MovieRepository
from app.services.movie_base_service import MovieBaseService
from app.services.movie_service import MovieService
from app.states.movie import UploadMovieState
from app.utils.checker import validate_bot_for_movie_base
from app.utils.movie_base_link import format_movie_base_link
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)


def _movie_database_error_message(error: SQLAlchemyError) -> str:
    if is_movie_title_schema_mismatch(error):
        return MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE

    return (
        "Kino yuklashda database xatoligi yuz berdi. "
        "Iltimos, loglarni tekshirib qayta urinib ko'ring."
    )


async def build_movie_base_upload_list(page: int):
    try:
        async with async_session_maker() as session:
            base_repository = MovieBaseRepository(session)
            base_service = MovieBaseService(base_repository)
            total_count = await base_service.count_bases_by_status(True)

            if total_count == 0:
                return None, None, 0

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            offset = (page - 1) * PAGE_SIZE
            bases = await base_service.get_paginated_bases_by_status(
                is_active=True,
                limit=PAGE_SIZE,
                offset=offset,
            )
    except SQLAlchemyError as error:
        logger.exception("Kino yuklash bazalari ro'yxatini olishda database xatosi")
        return _movie_database_error_message(error), None, 0

    text = (
        f"<b>Kino yuklash uchun bazani tanlang</b>\n"
        f"Sahifa: {page}/{total_pages}\n\n"
        "Tanlangan baza ichiga yuborgan media nusxasi saqlanadi."
    )
    keyboard = movie_base_selection_keyboard(
        bases=bases,
        page=page,
        total_pages=total_pages,
        callback_prefix="movie_upload",
        action_text="🎞",
    )
    return text, keyboard, page


@router.message(F.text == MOVIES_UPLOAD_BUTTON)
async def start_movie_upload(message: Message, state: FSMContext):
    text, keyboard, _ = await build_movie_base_upload_list(page=1)
    if not text:
        await state.clear()
        await message.answer(
            "Avval kamida bitta aktiv kino bazasi qo'shing.",
            reply_markup=movies_menu,
        )
        return

    await state.set_state(UploadMovieState.selecting_base)
    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(
    UploadMovieState.selecting_base,
    F.data.startswith("movie_upload:page:"),
)
async def paginate_movie_upload_bases(callback: CallbackQuery):
    page = int(callback.data.split(":")[2])
    text, keyboard, _ = await build_movie_base_upload_list(page=page)
    if not text:
        await callback.answer("Hozircha baza yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(
    UploadMovieState.selecting_base,
    F.data.startswith("movie_upload:select:"),
)
async def select_movie_upload_base(callback: CallbackQuery, state: FSMContext):
    _, _, movie_base_id_str, _ = callback.data.split(":")
    movie_base_id = int(movie_base_id_str)

    try:
        async with async_session_maker() as session:
            base_repository = MovieBaseRepository(session)
            base_service = MovieBaseService(base_repository)
            movie_base = await base_service.get_by_id(movie_base_id)
    except SQLAlchemyError as error:
        logger.exception("Tanlangan kino bazasini olishda database xatosi")
        await callback.answer(_movie_database_error_message(error), show_alert=True)
        return

    if not movie_base or not movie_base.is_active:
        await callback.answer("Baza topilmadi yoki noaktiv.", show_alert=True)
        return

    validation = await validate_bot_for_movie_base(callback.bot, movie_base.chat_id)
    if not validation.ok:
        await callback.answer(validation.message, show_alert=True)
        return

    await state.set_state(UploadMovieState.waiting_media)
    await state.update_data(movie_base_id=movie_base_id)
    await callback.message.edit_text(
        "Baza tanlandi.\n\n"
        f"<b>Nomi:</b> {safe_html(movie_base.title)}\n"
        f"<b>Turi:</b> {MovieBaseService.type_label(movie_base.base_type)}\n\n"
        "Endi video, document, animation, audio yoki photo yuboring.",
    )
    await callback.answer()


@router.callback_query(F.data == "movie_upload:current")
async def keep_movie_upload_page(callback: CallbackQuery):
    await callback.answer()


@router.message(UploadMovieState.waiting_media, F.content_type.in_({"video", "document", "animation", "audio", "photo"}))
async def save_movie_to_base(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_base_id = data.get("movie_base_id")

    if not movie_base_id:
        await state.clear()
        await message.answer(
            "Tanlangan baza topilmadi. Jarayonni qaytadan boshlang.",
            reply_markup=movies_menu,
        )
        return

    try:
        async with async_session_maker() as session:
            base_repository = MovieBaseRepository(session)
            movie_repository = MovieRepository(session)
            base_service = MovieBaseService(base_repository)
            movie_service = MovieService(movie_repository)
            movie_base = await base_service.get_by_id(movie_base_id)

            if not movie_base or not movie_base.is_active:
                await state.clear()
                await message.answer(
                    "Baza topilmadi yoki noaktiv. Jarayonni qaytadan boshlang.",
                    reply_markup=movies_menu,
                )
                return

            validation = await validate_bot_for_movie_base(message.bot, movie_base.chat_id)
            if not validation.ok:
                await message.answer(validation.message, reply_markup=cancel_keyboard)
                return

            result = await movie_service.upload_movie_to_base(
                bot=message.bot,
                movie_base=movie_base,
                source_message=message,
            )
    except SQLAlchemyError as error:
        logger.exception("Kino yuklash jarayonida database xatosi")
        await message.answer(_movie_database_error_message(error), reply_markup=cancel_keyboard)
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    movie = result["movie"]
    await state.clear()
    await message.answer(
        "✅ Kino bazaga saqlandi\n\n"
        f"🎬 Kino kodi: <code>{safe_html(movie.code)}</code>\n"
        f"<b>Baza nomi:</b> {safe_html(movie_base.title)}\n"
        f"<b>Baza linki:</b> {format_movie_base_link(movie_base)}\n"
        f"<b>Baza ID:</b> <code>{movie.movie_base_id}</code>\n"
        f"<b>Storage message ID:</b> <code>{movie.storage_message_id}</code>",
        reply_markup=movies_menu,
    )


@router.message(UploadMovieState.waiting_media)
async def invalid_movie_upload_input(message: Message):
    await message.answer(
        "Iltimos, video, document, animation, audio yoki photo yuboring.",
        reply_markup=cancel_keyboard,
    )


@router.channel_post(F.content_type.in_({"video", "document", "animation", "audio", "photo"}))
async def process_movie_base_channel_post(message: Message):
    try:
        async with async_session_maker() as session:
            base_repository = MovieBaseRepository(session)
            movie_repository = MovieRepository(session)
            base_service = MovieBaseService(base_repository)
            movie_service = MovieService(movie_repository)

            movie_base = await base_service.get_by_chat_id(message.chat.id)
            if not movie_base or not movie_base.is_active:
                return

            existing_movie = await movie_repository.get_by_storage_message(
                storage_chat_id=message.chat.id,
                storage_message_id=message.message_id,
            )
            if existing_movie:
                return

            await movie_service.process_channel_movie_post(
                bot=message.bot,
                movie_base=movie_base,
                channel_post=message,
            )
    except SQLAlchemyError:
        logger.exception("Kanal postini kino sifatida qayta ishlashda database xatosi")
