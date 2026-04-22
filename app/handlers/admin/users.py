import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.reply import admin_menu
from app.keyboards.admin.broadcast import broadcast_menu
from app.keyboards.admin.users import (
    BROADCAST_ACTIVE_BUTTON,
    BROADCAST_ALL_BUTTON,
    BROADCAST_INACTIVE_BUTTON,
    USERS_ACTIVE_BUTTON,
    USERS_ADMIN_BUTTON,
    USERS_BACK_BUTTON,
    USERS_BAN_BUTTON,
    USERS_BROADCAST_BUTTON,
    USERS_CANCEL_BUTTON,
    USERS_INACTIVE_BUTTON,
    USERS_PANEL_BUTTON,
    USERS_SEARCH_BUTTON,
    USERS_TOTAL_BUTTON,
    USERS_UNBAN_BUTTON,
    broadcast_audience_menu,
    users_cancel_menu,
    users_menu,
)
from app.keyboards.admin.users_inline import users_navigation_keyboard
from app.repositories.user_repository import UserRepository
from app.services.broadcast_service import BroadcastService
from app.services.user_management_service import UserManagementService
from app.states.user_management import BroadcastState, UserBanState, UserSearchState, UserUnbanState
from app.utils.callbacks import normalize_page, parse_callback_int

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

logger = logging.getLogger(__name__)

PAGE_SIZE = 5
USERS_ERROR_MESSAGE = (
    "Foydalanuvchilar bo'limida xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
)

AUDIENCE_BY_BUTTON = {
    BROADCAST_ALL_BUTTON: "all",
    BROADCAST_ACTIVE_BUTTON: "active",
    BROADCAST_INACTIVE_BUTTON: "inactive",
}

AUDIENCE_LABELS = {
    "all": "barcha userlar",
    "active": "aktiv userlar",
    "inactive": "noaktiv userlar",
}


async def _build_user_service(session) -> UserManagementService:
    return UserManagementService(UserRepository(session))


async def _answer_users_error(message: Message) -> None:
    await message.answer(USERS_ERROR_MESSAGE, reply_markup=users_menu)


@router.message(F.text == USERS_PANEL_BUTTON)
async def open_users_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👥 Foydalanuvchilar bo'limi.",
        reply_markup=users_menu,
    )


@router.message(F.text == USERS_TOTAL_BUTTON)
async def show_users_overview(message: Message):
    try:
        async with async_session_maker() as session:
            service = await _build_user_service(session)
            text = await service.build_user_overview(limit=10)
    except SQLAlchemyError:
        logger.exception("Foydalanuvchilar overview olishda database xatosi")
        await _answer_users_error(message)
        return

    await message.answer(text, reply_markup=users_menu)


@router.message(F.text == USERS_SEARCH_BUTTON)
async def start_user_search(message: Message, state: FSMContext):
    await state.set_state(UserSearchState.waiting_query)
    await message.answer(
        "Foydalanuvchini Telegram ID yoki username orqali yuboring.",
        reply_markup=users_cancel_menu,
    )


@router.message(UserSearchState.waiting_query)
async def finish_user_search(message: Message, state: FSMContext):
    if await _handle_users_common_buttons(message, state):
        return

    query = (message.text or "").strip()
    try:
        async with async_session_maker() as session:
            service = await _build_user_service(session)
            user = await service.search_user(query)
            if not user:
                await message.answer(
                    "Foydalanuvchi topilmadi. Telegram ID yoki username to'g'ri ekanini tekshiring.",
                    reply_markup=users_menu,
                )
                await state.clear()
                return

            text = await service.build_user_detail(user)
    except SQLAlchemyError:
        logger.exception("Foydalanuvchini qidirishda database xatosi")
        await _answer_users_error(message)
        await state.clear()
        return

    await state.clear()
    await message.answer(text, reply_markup=users_menu)


@router.message(F.text == USERS_ACTIVE_BUTTON)
async def show_active_users(message: Message):
    await _send_users_list(message, "active", page=1)


@router.message(F.text == USERS_INACTIVE_BUTTON)
async def show_inactive_users(message: Message):
    await _send_users_list(message, "inactive", page=1)


@router.callback_query(F.data.startswith("users_active:page:"))
async def paginate_active_users(callback: CallbackQuery):
    await _edit_users_list(
        callback,
        "active",
        normalize_page(parse_callback_int(callback.data, 2, default=1)),
    )


@router.callback_query(F.data.startswith("users_inactive:page:"))
async def paginate_inactive_users(callback: CallbackQuery):
    await _edit_users_list(
        callback,
        "inactive",
        normalize_page(parse_callback_int(callback.data, 2, default=1)),
    )


@router.callback_query(F.data.in_({"users_active:current", "users_inactive:current"}))
async def keep_users_page(callback: CallbackQuery):
    await callback.answer()


@router.message(F.text == USERS_BAN_BUTTON)
async def start_user_ban(message: Message, state: FSMContext):
    await state.set_state(UserBanState.waiting_query)
    await message.answer(
        "Ban qilinadigan foydalanuvchi Telegram ID yoki username qiymatini yuboring.",
        reply_markup=users_cancel_menu,
    )


@router.message(UserBanState.waiting_query)
async def finish_user_ban(message: Message, state: FSMContext):
    if await _handle_users_common_buttons(message, state):
        return

    try:
        async with async_session_maker() as session:
            service = await _build_user_service(session)
            result = await service.ban_user(message.text or "")
    except SQLAlchemyError:
        logger.exception("Foydalanuvchini ban qilishda database xatosi")
        await _answer_users_error(message)
        await state.clear()
        return

    await state.clear()
    await message.answer(result["message"], reply_markup=users_menu)


@router.message(F.text == USERS_UNBAN_BUTTON)
async def start_user_unban(message: Message, state: FSMContext):
    await state.set_state(UserUnbanState.waiting_query)
    await message.answer(
        "Bandan chiqariladigan foydalanuvchi Telegram ID yoki username qiymatini yuboring.",
        reply_markup=users_cancel_menu,
    )


@router.message(UserUnbanState.waiting_query)
async def finish_user_unban(message: Message, state: FSMContext):
    if await _handle_users_common_buttons(message, state):
        return

    try:
        async with async_session_maker() as session:
            service = await _build_user_service(session)
            result = await service.unban_user(message.text or "")
    except SQLAlchemyError:
        logger.exception("Foydalanuvchini bandan chiqarishda database xatosi")
        await _answer_users_error(message)
        await state.clear()
        return

    await state.clear()
    await message.answer(result["message"], reply_markup=users_menu)


@router.message(F.text == USERS_BROADCAST_BUTTON)
async def start_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Reklama yuborish yangi campaign tizimi orqali bajariladi.",
        reply_markup=broadcast_menu,
    )


@router.message(BroadcastState.choosing_audience)
async def choose_broadcast_audience(message: Message, state: FSMContext):
    if await _handle_users_common_buttons(message, state):
        return

    audience = AUDIENCE_BY_BUTTON.get(message.text or "")
    if not audience:
        await message.answer(
            "Iltimos, auditoriyani tugmalardan tanlang.",
            reply_markup=broadcast_audience_menu,
        )
        return

    await state.update_data(audience=audience)
    await state.set_state(BroadcastState.waiting_message)
    await message.answer(
        f"Broadcast matnini yuboring.\nAuditoriya: <b>{AUDIENCE_LABELS[audience]}</b>",
        reply_markup=users_cancel_menu,
    )


@router.message(BroadcastState.waiting_message)
async def send_broadcast(message: Message, state: FSMContext):
    if await _handle_users_common_buttons(message, state):
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Broadcast uchun matn yuboring.", reply_markup=users_cancel_menu)
        return

    data = await state.get_data()
    audience = data.get("audience", "all")
    await message.answer("Broadcast yuborish boshlandi. Natijani kuting...")

    try:
        async with async_session_maker() as session:
            service = BroadcastService(UserRepository(session))
            result = await service.send_broadcast(
                bot=message.bot,
                text=text,
                audience=audience,
            )
    except SQLAlchemyError:
        logger.exception("Broadcast uchun userlarni olishda database xatosi")
        await _answer_users_error(message)
        await state.clear()
        return

    await state.clear()
    await message.answer(
        "📢 <b>Broadcast yakunlandi</b>\n\n"
        f"Auditoriya: <b>{AUDIENCE_LABELS.get(audience, 'barcha userlar')}</b>\n"
        f"✅ Yuborildi: <b>{result['sent']}</b>\n"
        f"❌ Yuborilmadi: <b>{result['failed']}</b>",
        reply_markup=users_menu,
    )


@router.message(F.text == USERS_BACK_BUTTON)
async def users_back_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)


@router.message(F.text == USERS_ADMIN_BUTTON)
async def users_admin_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)


async def _send_users_list(message: Message, list_type: str, page: int) -> None:
    try:
        text, page, total_pages = await _build_users_list(list_type, page)
    except SQLAlchemyError:
        logger.exception("Foydalanuvchilar ro'yxatini olishda database xatosi")
        await _answer_users_error(message)
        return

    if not text:
        await message.answer("Bu ro'yxatda hozircha foydalanuvchi yo'q.", reply_markup=users_menu)
        return

    await message.answer(
        text,
        reply_markup=users_navigation_keyboard(
            page=page,
            total_pages=total_pages,
            callback_prefix=f"users_{list_type}",
        ),
    )


async def _edit_users_list(callback: CallbackQuery, list_type: str, page: int) -> None:
    page = normalize_page(page)
    try:
        text, page, total_pages = await _build_users_list(list_type, page)
    except SQLAlchemyError:
        logger.exception("Foydalanuvchilar pagination olishda database xatosi")
        await callback.answer("Ro'yxatni olishda xatolik yuz berdi.", show_alert=True)
        return

    if not text:
        await callback.answer("Bu ro'yxatda hozircha foydalanuvchi yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=users_navigation_keyboard(
            page=page,
            total_pages=total_pages,
            callback_prefix=f"users_{list_type}",
        ),
    )
    await callback.answer()


async def _build_users_list(list_type: str, page: int):
    async with async_session_maker() as session:
        service = await _build_user_service(session)
        return await service.build_users_list(
            list_type=list_type,
            page=page,
            page_size=PAGE_SIZE,
        )


async def _handle_users_common_buttons(message: Message, state: FSMContext) -> bool:
    if message.text == USERS_CANCEL_BUTTON:
        await state.clear()
        await message.answer("Amal bekor qilindi.", reply_markup=users_menu)
        return True

    if message.text == USERS_ADMIN_BUTTON:
        await state.clear()
        await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)
        return True

    if message.text == USERS_BACK_BUTTON:
        await state.clear()
        await message.answer("Foydalanuvchilar bo'limiga qaytdingiz.", reply_markup=users_menu)
        return True

    return False
