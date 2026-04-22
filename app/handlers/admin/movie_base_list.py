import math
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.movie_base_inline import movie_base_navigation_keyboard
from app.keyboards.admin.movies import MOVIES_LIST_BUTTON
from app.repositories.movie_base_repository import MovieBaseRepository
from app.services.movie_base_service import MovieBaseService
from app.utils.movie_base_link import format_movie_base_address
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)
MOVIE_BASE_ERROR_MESSAGE = (
    "Bazalar ro'yxatini olishda xatolik yuz berdi. Iltimos, loglarni tekshiring."
)


async def build_movie_base_list(page: int):
    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            total_count = await service.count_bases()

            if total_count == 0:
                return None, None

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            offset = (page - 1) * PAGE_SIZE
            bases = await service.get_paginated_bases(PAGE_SIZE, offset)
    except SQLAlchemyError:
        logger.exception("Kino bazalari ro'yxatini olishda database xatosi")
        return MOVIE_BASE_ERROR_MESSAGE, None

    lines = [f"<b>Kinolar bazalari ro'yxati</b>\nSahifa: {page}/{total_pages}\n"]

    for index, movie_base in enumerate(bases, start=offset + 1):
        status = "Aktiv" if movie_base.is_active else "Noaktiv"
        lines.append(
            f"{index}. <b>{safe_html(movie_base.title)}</b>\n"
            f"ID: <code>{movie_base.id}</code>\n"
            f"Turi: {MovieBaseService.type_label(movie_base.base_type)}\n"
            f"Manzil: {format_movie_base_address(movie_base)}\n"
            f"Holati: {status}\n"
        )

    return "\n".join(lines), movie_base_navigation_keyboard(
        page=page,
        total_pages=total_pages,
        callback_prefix="movie_base_list",
    )


@router.message(F.text == MOVIES_LIST_BUTTON)
async def show_movie_base_list(message: Message):
    text, keyboard = await build_movie_base_list(page=1)
    if not text:
        await message.answer("Hozircha kinolar bazalari yo'q.")
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith("movie_base_list:page:"))
async def paginate_movie_base_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[2])
    text, keyboard = await build_movie_base_list(page=page)
    if not text:
        await callback.answer("Hozircha kinolar bazalari yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data == "movie_base_list:current")
async def keep_movie_base_list_page(callback: CallbackQuery):
    await callback.answer()
