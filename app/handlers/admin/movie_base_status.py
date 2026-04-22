import logging
import math

from aiogram import F, Router
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.movie_base_inline import movie_base_selection_keyboard
from app.keyboards.admin.movies import (
    MOVIES_ACTIVATE_BASE_BUTTON,
    MOVIES_DEACTIVATE_BASE_BUTTON,
    movies_menu,
)
from app.repositories.movie_base_repository import MovieBaseRepository
from app.services.movie_base_service import MovieBaseService
from app.utils.callbacks import STALE_CALLBACK_MESSAGE, normalize_offset, normalize_page, parse_callback_int
from app.utils.movie_base_link import format_movie_base_address
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)
MOVIE_BASE_STATUS_ERROR_MESSAGE = (
    "Baza holatini o'zgartirishda database xatoligi yuz berdi. Iltimos, loglarni tekshiring."
)


async def build_movie_base_status_list(page: int, target_active: bool):
    page = normalize_page(page)
    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            source_active = not target_active
            total_count = await service.count_bases_by_status(source_active) or 0

            if total_count == 0:
                return None, None, 0

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            offset = normalize_offset((page - 1) * PAGE_SIZE)
            bases = await service.get_paginated_bases_by_status(
                is_active=source_active,
                limit=PAGE_SIZE,
                offset=offset,
            )
    except SQLAlchemyError:
        logger.exception("Kino bazalari status ro'yxatini olishda database xatosi")
        return MOVIE_BASE_STATUS_ERROR_MESSAGE, None, 0

    action_text = "aktiv qilish" if target_active else "noaktiv qilish"
    status_text = "Noaktiv" if target_active else "Aktiv"
    lines = [
        f"<b>{action_text.capitalize()} uchun bazani tanlang</b>",
        f"Sahifa: {page}/{total_pages}",
        f"Ko'rsatilayotgan holat: {status_text}",
        "",
    ]

    bases = list(bases or [])
    if not bases:
        return "Bazalar topilmadi.", None, page

    for index, movie_base in enumerate(bases, start=offset + 1):
        status = "Aktiv" if movie_base.is_active else "Noaktiv"
        lines.append(
            f"{index}. <b>{safe_html(movie_base.title)}</b>\n"
            f"ID: <code>{movie_base.id}</code>\n"
            f"Turi: {MovieBaseService.type_label(movie_base.base_type)}\n"
            f"Manzil: {format_movie_base_address(movie_base)}\n"
            f"Holati: {status}\n"
        )

    callback_prefix = "movie_base_activate" if target_active else "movie_base_deactivate"
    button_text = "✅ Aktiv qilish" if target_active else "⛔ Noaktiv qilish"
    keyboard = movie_base_selection_keyboard(
        bases=bases,
        page=page,
        total_pages=total_pages,
        callback_prefix=callback_prefix,
        action_text=button_text,
    )
    return "\n".join(lines), keyboard, page


@router.message(F.text == MOVIES_ACTIVATE_BASE_BUTTON)
async def show_inactive_movie_bases(message: Message):
    text, keyboard, _ = await build_movie_base_status_list(page=1, target_active=True)
    if not text:
        await message.answer("Aktiv qilinadigan noaktiv baza yo'q.", reply_markup=movies_menu)
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.message(F.text == MOVIES_DEACTIVATE_BASE_BUTTON)
async def show_active_movie_bases(message: Message):
    text, keyboard, _ = await build_movie_base_status_list(page=1, target_active=False)
    if not text:
        await message.answer("Noaktiv qilinadigan aktiv baza yo'q.", reply_markup=movies_menu)
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith("movie_base_activate:page:"))
async def paginate_inactive_movie_bases(callback: CallbackQuery):
    page = normalize_page(parse_callback_int(callback.data, 2, default=1))
    text, keyboard, _ = await build_movie_base_status_list(page=page, target_active=True)
    if not text:
        await callback.answer("Aktiv qilinadigan baza yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movie_base_deactivate:page:"))
async def paginate_active_movie_bases(callback: CallbackQuery):
    page = normalize_page(parse_callback_int(callback.data, 2, default=1))
    text, keyboard, _ = await build_movie_base_status_list(page=page, target_active=False)
    if not text:
        await callback.answer("Noaktiv qilinadigan baza yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data == "movie_base_activate:current")
@router.callback_query(F.data == "movie_base_deactivate:current")
async def keep_movie_base_status_page(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("movie_base_activate:select:"))
async def activate_movie_base(callback: CallbackQuery):
    base_id = parse_callback_int(callback.data, 2)
    if base_id is None:
        await callback.answer(STALE_CALLBACK_MESSAGE, show_alert=True)
        return
    await _set_movie_base_status(
        callback,
        base_id=base_id,
        page=normalize_page(parse_callback_int(callback.data, 3, default=1)),
        target_active=True,
    )


@router.callback_query(F.data.startswith("movie_base_deactivate:select:"))
async def deactivate_movie_base(callback: CallbackQuery):
    base_id = parse_callback_int(callback.data, 2)
    if base_id is None:
        await callback.answer(STALE_CALLBACK_MESSAGE, show_alert=True)
        return
    await _set_movie_base_status(
        callback,
        base_id=base_id,
        page=normalize_page(parse_callback_int(callback.data, 3, default=1)),
        target_active=False,
    )


async def _set_movie_base_status(
    callback: CallbackQuery,
    base_id: int,
    page: int,
    target_active: bool,
):
    page = normalize_page(page)
    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            result = (
                await service.activate_base(base_id)
                if target_active
                else await service.deactivate_base(base_id)
            )
    except SQLAlchemyError:
        logger.exception("Kino bazasi statusini o'zgartirishda database xatosi")
        await callback.answer(MOVIE_BASE_STATUS_ERROR_MESSAGE, show_alert=True)
        return

    if not result["ok"]:
        await callback.answer(result["message"], show_alert=True)
        return

    text, keyboard, _ = await build_movie_base_status_list(
        page=page,
        target_active=target_active,
    )
    if not text:
        await callback.message.edit_text(result["message"])
        await callback.answer(result["message"])
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer(result["message"])
