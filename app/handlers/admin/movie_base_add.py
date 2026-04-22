from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.movies import (
    MOVIES_PRIVATE_BASE_BUTTON,
    MOVIES_PUBLIC_BASE_BUTTON,
    movies_menu,
)
from app.repositories.movie_base_repository import MovieBaseRepository
from app.services.movie_base_service import MovieBaseService
from app.states.movie import AddPrivateMovieBaseState, AddPublicMovieBaseState
from app.utils.checker import validate_bot_for_movie_base
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
logger = logging.getLogger(__name__)
MOVIE_BASE_SAVE_ERROR_MESSAGE = (
    "Kino bazasini saqlashda vaqtinchalik database xatosi yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
)


def _extract_forwarded_chat_id(message: types.Message) -> int | None:
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat = message.forward_origin.chat
        if chat:
            return chat.id

    if message.forward_from_chat:
        return message.forward_from_chat.id

    return None


@router.message(F.text == MOVIES_PUBLIC_BASE_BUTTON)
async def start_add_public_movie_base(message: types.Message, state: FSMContext):
    await state.set_state(AddPublicMovieBaseState.channel_reference)
    await message.answer(
        "Ommaviy kanal username yoki linkini yuboring.\n\n"
        "Masalan:\n<code>@my_movie_base</code>\n"
        "yoki\n<code>https://t.me/my_movie_base</code>",
        reply_markup=cancel_keyboard,
    )


@router.message(
    AddPublicMovieBaseState.channel_reference,
    F.text,
    F.text != CANCEL_BUTTON,
)
async def handle_public_movie_base_reference(message: types.Message, state: FSMContext):
    raw_value = (message.text or "").strip()
    service = MovieBaseService(None)
    username, invite_link = service.normalize_public_reference(raw_value)

    if not username or not invite_link:
        await message.answer(
            "Ommaviy kanal uchun to'g'ri username yoki link yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    try:
        chat = await message.bot.get_chat(username)
    except TelegramBadRequest:
        await message.answer(
            "Kanal topilmadi. Username yoki havolani qayta tekshirib yuboring.",
            reply_markup=cancel_keyboard,
        )
        return
    except TelegramAPIError:
        await message.answer(
            "Kanalni tekshirib bo'lmadi. Bot kanalga qo'shilganini tekshiring.",
            reply_markup=cancel_keyboard,
        )
        return

    if chat.type != "channel":
        await message.answer(
            "Faqat kanalni baza sifatida qo'shish mumkin.",
            reply_markup=cancel_keyboard,
        )
        return

    validation = await validate_bot_for_movie_base(message.bot, chat.id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=cancel_keyboard,
        )
        return

    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            result = await service.create_public_base(
                title=chat.title or "Noma'lum kanal",
                chat_username=username,
                chat_id=chat.id,
                invite_link=invite_link,
            )
    except SQLAlchemyError:
        logger.exception("Ommaviy kino bazani saqlashda database xatosi | chat_id=%s", chat.id)
        await message.answer(MOVIE_BASE_SAVE_ERROR_MESSAGE, reply_markup=cancel_keyboard)
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    movie_base = result["movie_base"]
    await state.clear()
    await message.answer(
        "Ommaviy kino bazasi saqlandi.\n\n"
        f"<b>Nomi:</b> {safe_html(movie_base.title)}\n"
        f"<b>Username:</b> {safe_html(movie_base.chat_username)}\n"
        f"<b>Chat ID:</b> <code>{movie_base.chat_id}</code>",
        reply_markup=movies_menu,
    )


@router.message(AddPublicMovieBaseState.channel_reference)
async def invalid_public_movie_base_input(message: types.Message):
    await message.answer(
        "Iltimos, kanal username yoki havolasini matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )


@router.message(F.text == MOVIES_PRIVATE_BASE_BUTTON)
async def start_add_private_movie_base(message: types.Message, state: FSMContext):
    await state.set_state(AddPrivateMovieBaseState.invite_link)
    await message.answer(
        "Maxfiy kanal qo'shish uchun avval kanal invite linkini yuboring.\n\n"
        "Masalan: <code>https://t.me/+abc123xyz</code>\n"
        "Agar bot link orqali kanalni tekshira olmasa, keyingi qadamda shu kanaldan forward qilingan post ham so'raladi.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateMovieBaseState.invite_link, F.text, F.text != CANCEL_BUTTON)
async def handle_private_movie_base_invite_link(message: types.Message, state: FSMContext):
    raw_invite_link = (message.text or "").strip()

    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            invite_link, error = service.normalize_private_invite_link(raw_invite_link)
    except SQLAlchemyError:
        logger.exception("Maxfiy kino baza invite link tekshirishda database xatosi")
        await message.answer(MOVIE_BASE_SAVE_ERROR_MESSAGE, reply_markup=cancel_keyboard)
        return

    if error:
        await message.answer(
            f"{error}\n\nIltimos, maxfiy kanal invite linkini qayta yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    await state.update_data(invite_link=invite_link)
    await state.set_state(AddPrivateMovieBaseState.chat_reference)
    await message.answer(
        "Havola qabul qilindi.\n\n"
        "Endi botni maxfiy kanalga admin qiling va shu kanaldan istalgan postni forward qiling.\n"
        "Agar chat ID ma'lum bo'lsa, uni ham yuborishingiz mumkin.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateMovieBaseState.invite_link)
async def invalid_private_movie_base_invite_link(message: types.Message):
    await message.answer(
        "Iltimos, maxfiy kanal invite linkini matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateMovieBaseState.chat_reference, F.text, F.text != CANCEL_BUTTON)
async def handle_private_movie_base_chat_id(message: types.Message, state: FSMContext):
    forwarded_chat_id = _extract_forwarded_chat_id(message)
    if forwarded_chat_id:
        await _save_private_movie_base(message, state, forwarded_chat_id)
        return

    chat_reference = (message.text or "").strip()

    if not chat_reference.lstrip("-").isdigit():
        await message.answer(
            "Chat ID noto'g'ri. Raqam ko'rinishida yuboring yoki forward qilingan post yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    await _save_private_movie_base(message, state, int(chat_reference))


@router.message(AddPrivateMovieBaseState.chat_reference)
async def handle_private_movie_base_forward(message: types.Message, state: FSMContext):
    chat_id = _extract_forwarded_chat_id(message)
    if not chat_id:
        await message.answer(
            "Iltimos, chat ID yoki forward qilingan post yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    await _save_private_movie_base(message, state, chat_id)


async def _save_private_movie_base(message: types.Message, state: FSMContext, chat_id: int):
    data = await state.get_data()
    invite_link = data.get("invite_link")

    if not invite_link:
        await state.set_state(AddPrivateMovieBaseState.invite_link)
        await message.answer(
            "Invite link topilmadi. Iltimos, maxfiy kanal havolasini qayta yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    try:
        chat = await message.bot.get_chat(chat_id)
    except TelegramBadRequest:
        await message.answer(
            "Kanal topilmadi yoki bot kanalni ko'ra olmayapti.",
            reply_markup=cancel_keyboard,
        )
        return
    except TelegramAPIError:
        await message.answer(
            "Kanalni tekshirib bo'lmadi. Bot kanalga qo'shilganini tekshiring.",
            reply_markup=cancel_keyboard,
        )
        return

    if chat.type != "channel":
        await message.answer(
            "Faqat kanalni baza sifatida qo'shish mumkin.",
            reply_markup=cancel_keyboard,
        )
        return

    if chat.username:
        await message.answer(
            "Bu ommaviy kanal ko'rinmoqda. Uni 'Ommaviy kanal qo'shish' orqali kiriting.",
            reply_markup=cancel_keyboard,
        )
        return

    validation = await validate_bot_for_movie_base(message.bot, chat_id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=cancel_keyboard,
        )
        return

    try:
        async with async_session_maker() as session:
            repository = MovieBaseRepository(session)
            service = MovieBaseService(repository)
            result = await service.create_private_base(
                title=chat.title or f"Private channel {chat_id}",
                chat_id=chat_id,
                invite_link=invite_link,
            )
    except SQLAlchemyError:
        logger.exception("Maxfiy kino bazani saqlashda database xatosi | chat_id=%s", chat_id)
        await message.answer(MOVIE_BASE_SAVE_ERROR_MESSAGE, reply_markup=cancel_keyboard)
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    movie_base = result["movie_base"]
    await state.clear()
    await message.answer(
        "Maxfiy kino bazasi saqlandi.\n\n"
        f"<b>Nomi:</b> {safe_html(movie_base.title)}\n"
        f"<b>Chat ID:</b> <code>{movie_base.chat_id}</code>\n"
        f"<b>Havola:</b> <a href=\"{safe_html(movie_base.invite_link)}\">Ochish</a>",
        reply_markup=movies_menu,
    )
