import math
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.errors import (
    MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE,
    is_movie_title_schema_mismatch,
)
from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.movie_inline import (
    movie_delete_options_keyboard,
    movie_list_keyboard,
    movie_navigation_keyboard,
)
from app.keyboards.admin.movies import (
    MOVIES_ADMIN_BUTTON,
    MOVIES_DELETE_CANCEL_BUTTON,
    MOVIES_DELETE_MOVIE_BUTTON,
    MOVIES_SAVED_LIST_BUTTON,
    movie_delete_menu,
    movies_menu,
)
from app.keyboards.admin.reply import admin_menu
from app.repositories.movie_repository import MovieRepository
from app.states.movie import DeleteMovieState
from app.utils.checker import check_bot_permissions
from app.utils.movie_admin_preview import build_movie_admin_preview
from app.utils.movie_code import is_movie_code

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)


def _movie_database_error_message(error: SQLAlchemyError) -> str:
    if is_movie_title_schema_mismatch(error):
        return MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE

    return (
        "Kinolar bilan ishlashda database xatoligi yuz berdi. "
        "Iltimos, loglarni tekshirib qayta urinib ko'ring."
    )


async def build_saved_movies_list(page: int, delete_mode: bool = False):
    try:
        async with async_session_maker() as session:
            repository = MovieRepository(session)
            total_count = await repository.count_active()

            if total_count == 0:
                return None, None, 0

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            offset = (page - 1) * PAGE_SIZE
            movies = await repository.list_movies(PAGE_SIZE, offset)
    except SQLAlchemyError as error:
        logger.exception("Kinolar ro'yxatini olishda database xatosi")
        return (
            _movie_database_error_message(error),
            None,
            0,
        )

    title = "O'chirish uchun kinoni tanlang" if delete_mode else "Saqlangan kinolar ro'yxati"
    lines = [f"<b>{title}</b>\nSahifa: {page}/{total_pages}\n"]

    for index, (movie, movie_base) in enumerate(movies, start=offset + 1):
        lines.append(build_movie_admin_preview(movie, movie_base, index=index))

    if delete_mode:
        keyboard = movie_list_keyboard(
            movies,
            page=page,
            total_pages=total_pages,
            navigation_callback_prefix="movie_delete",
        )
    else:
        keyboard = movie_navigation_keyboard(
            page=page,
            total_pages=total_pages,
            callback_prefix="movie_list",
        )

    return "\n\n".join(lines), keyboard, page


@router.message(F.text == MOVIES_SAVED_LIST_BUTTON)
async def show_saved_movies(message: Message, state: FSMContext):
    await state.clear()
    text, keyboard, _ = await build_saved_movies_list(page=1)
    if not text:
        await message.answer("Hozircha saqlangan kino yo'q.", reply_markup=movies_menu)
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith("movie_list:page:"))
async def paginate_saved_movies(callback: CallbackQuery):
    page = int(callback.data.split(":")[2])
    text, keyboard, _ = await build_saved_movies_list(page=page)
    if not text:
        await callback.answer("Hozircha saqlangan kino yo'q.", show_alert=True)
        return

    if not keyboard:
        await callback.message.edit_text(text)
        await callback.answer()
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data == "movie_list:current")
async def keep_saved_movies_page(callback: CallbackQuery):
    await callback.answer()


@router.message(F.text == MOVIES_DELETE_MOVIE_BUTTON)
async def show_movie_delete_menu(message: Message, state: FSMContext):
    text, keyboard, _ = await build_saved_movies_list(page=1, delete_mode=True)
    if not text:
        await state.clear()
        await message.answer("Hozircha o'chiriladigan kino yo'q.", reply_markup=movies_menu)
        return
    if not keyboard:
        await state.clear()
        await message.answer(text, reply_markup=movies_menu)
        return

    await state.set_state(DeleteMovieState.waiting_code)
    await message.answer(
        "Kinoni o'chirish bo'limi ochildi.",
        reply_markup=movie_delete_menu,
    )
    await message.answer(
        text + "\n\nKino kodini ham yuborishingiz mumkin. Masalan: <code>0001</code>",
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(
    DeleteMovieState.waiting_code,
    F.data.startswith("movie_delete:page:"),
)
async def paginate_movie_delete_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[2])
    text, keyboard, _ = await build_saved_movies_list(page=page, delete_mode=True)
    if not text:
        await callback.answer("Hozircha saqlangan kino yo'q.", show_alert=True)
        return

    if not keyboard:
        await callback.message.edit_text(text)
        await callback.answer()
        return

    await callback.message.edit_text(
        text + "\n\nKino kodini ham yuborishingiz mumkin. Masalan: <code>0001</code>",
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data == "movie_delete:current")
async def keep_movie_delete_page(callback: CallbackQuery):
    await callback.answer()


@router.message(DeleteMovieState.waiting_code, F.text == MOVIES_DELETE_CANCEL_BUTTON)
@router.message(DeleteMovieState.confirming, F.text == MOVIES_DELETE_CANCEL_BUTTON)
async def cancel_movie_delete_by_reply(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Kinoni o'chirish bekor qilindi",
        reply_markup=movies_menu,
    )


@router.message(DeleteMovieState.waiting_code, F.text == MOVIES_ADMIN_BUTTON)
@router.message(DeleteMovieState.confirming, F.text == MOVIES_ADMIN_BUTTON)
async def movie_delete_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu,
    )


@router.callback_query(F.data.startswith("movie_delete:select:"))
async def select_movie_to_delete(callback: CallbackQuery, state: FSMContext):
    _, _, code, page_str = callback.data.split(":")
    await _show_delete_confirmation(callback, state, code=code, page=int(page_str))


@router.message(DeleteMovieState.waiting_code, F.text)
async def receive_movie_delete_code(message: Message, state: FSMContext):
    code = (message.text or "").strip()
    if not is_movie_code(code):
        await message.answer("Iltimos, 4 xonali kino kodini yuboring. Masalan: <code>0001</code>")
        return

    try:
        async with async_session_maker() as session:
            repository = MovieRepository(session)
            movie_with_base = await repository.get_by_code_with_base(code)
    except SQLAlchemyError as error:
        logger.exception("O'chiriladigan kinoni tekshirishda database xatosi")
        await message.answer(_movie_database_error_message(error))
        return

    if not movie_with_base:
        await message.answer("Bunday kino topilmadi. Kod noto'g'ri yoki kino hozircha mavjud emas.")
        return

    await state.set_state(DeleteMovieState.confirming)
    await state.update_data(movie_code=code, page=1)
    await message.answer(
        "Quyidagi kino tanlandi:\n\n"
        f"{build_movie_admin_preview(*movie_with_base)}\n\n"
        "Ushbu kinoni qanday o'chirmoqchisiz?",
        reply_markup=movie_delete_options_keyboard(code, page=1),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def _show_delete_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    code: str,
    page: int,
):
    try:
        async with async_session_maker() as session:
            repository = MovieRepository(session)
            movie_with_base = await repository.get_by_code_with_base(code)
    except SQLAlchemyError as error:
        logger.exception("O'chiriladigan kinoni callback orqali tekshirishda database xatosi")
        await callback.answer(_movie_database_error_message(error), show_alert=True)
        return

    if not movie_with_base:
        await callback.answer("Kino topilmadi.", show_alert=True)
        return

    await state.set_state(DeleteMovieState.confirming)
    await state.update_data(movie_code=code, page=page)
    await callback.message.edit_text(
        "Quyidagi kino tanlandi:\n\n"
        f"{build_movie_admin_preview(*movie_with_base)}\n\n"
        "Ushbu kinoni qanday o'chirmoqchisiz?",
        reply_markup=movie_delete_options_keyboard(code, page),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(
    DeleteMovieState.confirming,
    F.data.startswith("movie_delete:db:"),
)
async def delete_movie_from_bot_only(callback: CallbackQuery, state: FSMContext):
    _, _, code, page_str = callback.data.split(":")
    await _delete_movie(callback, state, code=code, page=int(page_str), delete_channel_post=False)


@router.callback_query(
    DeleteMovieState.confirming,
    F.data.startswith("movie_delete:channel:"),
)
async def delete_movie_from_bot_and_channel(callback: CallbackQuery, state: FSMContext):
    _, _, code, page_str = callback.data.split(":")
    await _delete_movie(callback, state, code=code, page=int(page_str), delete_channel_post=True)


async def _delete_movie(
    callback: CallbackQuery,
    state: FSMContext,
    code: str,
    page: int,
    delete_channel_post: bool,
):
    movie = None
    if delete_channel_post:
        try:
            async with async_session_maker() as session:
                repository = MovieRepository(session)
                movie = await repository.get_by_code(code)
        except SQLAlchemyError as error:
            logger.exception("Kanaldan o'chiriladigan kino ma'lumotini olishda database xatosi")
            await callback.answer(_movie_database_error_message(error), show_alert=True)
            return

        if not movie:
            await callback.answer("Kino topilmadi.", show_alert=True)
            return

        validation = await check_bot_permissions(
            callback.bot,
            movie.storage_chat_id,
            can_delete_messages=True,
        )
        if not validation.ok:
            await callback.answer(validation.message, show_alert=True)
            return

        try:
            await callback.bot.delete_message(
                chat_id=movie.storage_chat_id,
                message_id=movie.storage_message_id,
            )
        except TelegramBadRequest:
            logger.exception(
                "Kanal postini o'chirishda Telegram xatosi: code=%s chat_id=%s message_id=%s",
                code,
                movie.storage_chat_id,
                movie.storage_message_id,
            )
            await callback.answer(
                "Kanal postini o'chirib bo'lmadi. Bot kanalda admin va xabarlarni o'chirish huquqiga ega ekanini tekshiring.",
                show_alert=True,
            )
            return

    try:
        async with async_session_maker() as session:
            repository = MovieRepository(session)
            deleted = await repository.delete_movie(code)
    except SQLAlchemyError as error:
        logger.exception("Kinoni o'chirishda database xatosi")
        await callback.answer(_movie_database_error_message(error), show_alert=True)
        return

    if not deleted:
        await callback.answer("Kino topilmadi.", show_alert=True)
        return

    delete_result_text = (
        "Kino botdan va kanaldan o'chirildi."
        if delete_channel_post
        else "Kino botdan o'chirildi. Kanal posti saqlandi."
    )
    text, keyboard, _ = await build_saved_movies_list(page=page, delete_mode=True)
    if not text:
        await state.clear()
        await callback.message.edit_text(f"{delete_result_text} Hozircha saqlangan kino yo'q.")
        await callback.answer(delete_result_text)
        return
    if not keyboard:
        await state.clear()
        await callback.message.edit_text(text)
        await callback.answer(delete_result_text)
        return

    await state.set_state(DeleteMovieState.waiting_code)
    await callback.message.edit_text(
        text + "\n\nKino kodini ham yuborishingiz mumkin. Masalan: <code>0001</code>",
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer(delete_result_text)


@router.callback_query(
    DeleteMovieState.confirming,
    F.data.startswith("movie_delete:cancel:"),
)
async def cancel_movie_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Kinoni o'chirish bekor qilindi.")
    await callback.message.answer("Kino bo'limiga qaytdingiz.", reply_markup=movies_menu)
    await callback.answer("O'chirish bekor qilindi.")
