import math
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.movie_base_inline import (
    movie_base_delete_confirmation_keyboard,
    movie_base_selection_keyboard,
)
from app.keyboards.admin.movies import MOVIES_DELETE_BUTTON, movies_menu
from app.repositories.movie_base_repository import MovieBaseRepository
from app.services.movie_base_service import MovieBaseService
from app.states.movie import DeleteMovieBaseState
from app.utils.callbacks import STALE_CALLBACK_MESSAGE, normalize_offset, normalize_page, parse_callback_int
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)
MOVIE_BASE_DELETE_ERROR_MESSAGE = (
    "Bazani o'chirish bo'limida database xatoligi yuz berdi. Iltimos, loglarni tekshiring."
)


async def build_movie_base_delete_list(page: int):
    page = normalize_page(page)
    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            total_count = await service.count_bases() or 0

            if total_count == 0:
                return None, None, 0

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            offset = normalize_offset((page - 1) * PAGE_SIZE)
            bases = await service.get_paginated_bases(PAGE_SIZE, offset)
    except SQLAlchemyError:
        logger.exception("O'chiriladigan kino bazalari ro'yxatini olishda database xatosi")
        return MOVIE_BASE_DELETE_ERROR_MESSAGE, None, 0

    bases = list(bases or [])
    if not bases:
        return "Bazalar topilmadi.", None, page

    lines = [f"<b>O'chirish uchun bazani tanlang</b>\nSahifa: {page}/{total_pages}\n"]
    for index, movie_base in enumerate(bases, start=offset + 1):
        lines.append(
            f"{index}. <b>{safe_html(movie_base.title)}</b>\n"
            f"ID: <code>{movie_base.id}</code>\n"
            f"Turi: {MovieBaseService.type_label(movie_base.base_type)}\n"
        )

    keyboard = movie_base_selection_keyboard(
        bases=bases,
        page=page,
        total_pages=total_pages,
        callback_prefix="movie_base_delete",
        action_text="🗑",
    )
    return "\n".join(lines), keyboard, page


@router.message(F.text == MOVIES_DELETE_BUTTON)
async def show_movie_base_delete_menu(message: Message, state: FSMContext):
    text, keyboard, _ = await build_movie_base_delete_list(page=1)
    if not text:
        await state.clear()
        await message.answer("Hozircha o'chiriladigan baza yo'q.", reply_markup=movies_menu)
        return

    await state.set_state(DeleteMovieBaseState.selecting)
    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(
    DeleteMovieBaseState.selecting,
    F.data.startswith("movie_base_delete:page:"),
)
async def paginate_movie_base_delete_list(callback: CallbackQuery):
    page = normalize_page(parse_callback_int(callback.data, 2, default=1))
    text, keyboard, _ = await build_movie_base_delete_list(page=page)
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
    DeleteMovieBaseState.selecting,
    F.data.startswith("movie_base_delete:select:"),
)
async def confirm_movie_base_delete(callback: CallbackQuery, state: FSMContext):
    movie_base_id = parse_callback_int(callback.data, 2)
    page = normalize_page(parse_callback_int(callback.data, 3, default=1))
    if movie_base_id is None:
        await callback.answer(STALE_CALLBACK_MESSAGE, show_alert=True)
        return

    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            movie_base = await service.get_by_id(movie_base_id)
    except SQLAlchemyError:
        logger.exception("O'chiriladigan bazani olishda database xatosi")
        await callback.answer(MOVIE_BASE_DELETE_ERROR_MESSAGE, show_alert=True)
        return

    if not movie_base:
        await callback.answer("Baza topilmadi.", show_alert=True)
        return

    await state.set_state(DeleteMovieBaseState.confirming)
    await state.update_data(movie_base_id=movie_base_id, page=page)
    await callback.message.edit_text(
        "Quyidagi bazani o'chirmoqchimisiz?\n\n"
        f"<b>{safe_html(movie_base.title)}</b>\n"
        f"Turi: {MovieBaseService.type_label(movie_base.base_type)}\n\n"
        "Diqqat: bu bazaga bog'langan kinolar ham o'chadi.",
        reply_markup=movie_base_delete_confirmation_keyboard(movie_base_id, page),
    )
    await callback.answer()


@router.callback_query(
    DeleteMovieBaseState.confirming,
    F.data.startswith("movie_base_delete:confirm:"),
)
async def delete_movie_base(callback: CallbackQuery, state: FSMContext):
    movie_base_id = parse_callback_int(callback.data, 2)
    page = normalize_page(parse_callback_int(callback.data, 3, default=1))
    if movie_base_id is None:
        await callback.answer(STALE_CALLBACK_MESSAGE, show_alert=True)
        return

    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            deleted = await service.delete_base(movie_base_id)
    except SQLAlchemyError:
        logger.exception("Kino bazasini o'chirishda database xatosi")
        await callback.answer(MOVIE_BASE_DELETE_ERROR_MESSAGE, show_alert=True)
        return

    if not deleted:
        await callback.answer("Baza topilmadi.", show_alert=True)
        return

    text, keyboard, _ = await build_movie_base_delete_list(page=page)
    if not text:
        await state.clear()
        await callback.message.edit_text("Barcha bazalar o'chirildi.")
        await callback.answer("Baza o'chirildi.")
        return

    await state.set_state(DeleteMovieBaseState.selecting)
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer("Baza o'chirildi.")


@router.callback_query(
    DeleteMovieBaseState.confirming,
    F.data.startswith("movie_base_delete:cancel:"),
)
async def cancel_movie_base_delete(callback: CallbackQuery, state: FSMContext):
    page = normalize_page(parse_callback_int(callback.data, 2, default=1))
    text, keyboard, _ = await build_movie_base_delete_list(page=page)
    if not text:
        await state.clear()
        await callback.message.edit_text("Hozircha baza yo'q.")
        await callback.answer()
        return

    await state.set_state(DeleteMovieBaseState.selecting)
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer("O'chirish bekor qilindi.")


@router.callback_query(F.data == "movie_base_delete:current")
async def keep_movie_base_delete_page(callback: CallbackQuery):
    await callback.answer()
