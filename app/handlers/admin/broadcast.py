import logging

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.broadcast import (
    BROADCAST_ADMIN_BUTTON,
    BROADCAST_ALL_BUTTON,
    BROADCAST_BACK_BUTTON,
    BROADCAST_CANCEL_BUTTON,
    BROADCAST_CANCEL_JOB_BUTTON,
    BROADCAST_CANCEL_JOB_CANCEL_CALLBACK,
    BROADCAST_CANCEL_JOB_CONFIRM_CALLBACK,
    BROADCAST_CHANNELS_BUTTON,
    BROADCAST_CONFIRM_BUTTON,
    BROADCAST_DELETE_BUTTON,
    BROADCAST_DELETE_CANCEL_CALLBACK,
    BROADCAST_DELETE_CONFIRM_CALLBACK,
    BROADCAST_GROUPS_BUTTON,
    BROADCAST_HISTORY_BUTTON,
    BROADCAST_PANEL_BUTTON,
    BROADCAST_SEND_BUTTON,
    BROADCAST_USERS_BUTTON,
    broadcast_cancel_job_confirm_inline_keyboard,
    broadcast_cancel_menu,
    broadcast_confirm_menu,
    broadcast_delete_confirm_inline_keyboard,
    broadcast_menu,
    broadcast_target_menu,
)
from app.keyboards.admin.reply import admin_menu
from app.repositories.broadcast_repository import BroadcastRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.broadcast_service import BroadcastService
from app.states.broadcast import BroadcastCancelState, BroadcastDeleteState, BroadcastSendState

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

logger = logging.getLogger(__name__)

BROADCAST_ERROR_MESSAGE = (
    "Reklama bo'limida xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
)

TARGET_BY_BUTTON = {
    BROADCAST_USERS_BUTTON: "users",
    BROADCAST_GROUPS_BUTTON: "groups",
    BROADCAST_CHANNELS_BUTTON: "channels",
    BROADCAST_ALL_BUTTON: "all",
}

SUPPORTED_CONTENT_TYPES = {
    "text",
    "photo",
    "video",
    "document",
    "animation",
    "audio",
    "voice",
}


def _build_broadcast_service(session) -> BroadcastService:
    return BroadcastService(
        user_repository=UserRepository(session),
        broadcast_repository=BroadcastRepository(session),
        subscription_repository=SubscriptionRepository(session),
    )


@router.message(F.text == BROADCAST_PANEL_BUTTON)
async def open_broadcast_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📣 Reklama bo'limi.",
        reply_markup=broadcast_menu,
    )


@router.message(F.text == BROADCAST_SEND_BUTTON)
async def start_broadcast_send(message: types.Message, state: FSMContext):
    await state.set_state(BroadcastSendState.waiting_post)
    await message.answer(
        "Tayyor reklama postini yuboring. Matn, photo + caption, video + caption yoki hujjat qabul qilinadi.",
        reply_markup=broadcast_cancel_menu,
    )


@router.message(BroadcastSendState.waiting_post)
async def receive_broadcast_post(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    content_type = _message_content_type(message)
    if content_type not in SUPPORTED_CONTENT_TYPES:
        await message.answer(
            "Bu format hozircha qo'llab-quvvatlanmaydi. Matn, photo, video yoki hujjat yuboring.",
            reply_markup=broadcast_cancel_menu,
        )
        return

    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        content_type=content_type,
        text=message.html_text,
        file_id=_message_file_id(message, content_type),
    )
    await state.set_state(BroadcastSendState.choosing_target)
    await message.answer(
        "Reklama kimlarga yuborilsin?",
        reply_markup=broadcast_target_menu,
    )


@router.message(BroadcastSendState.choosing_target)
async def choose_broadcast_target(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    target_type = TARGET_BY_BUTTON.get(message.text or "")
    if not target_type:
        await message.answer(
            "Iltimos, auditoriyani tugmalardan tanlang.",
            reply_markup=broadcast_target_menu,
        )
        return

    data = await state.get_data()
    await state.update_data(target_type=target_type)
    await state.set_state(BroadcastSendState.confirming)

    service = BroadcastService(user_repository=None)
    await message.answer(
        service.build_campaign_preview(
            content_type=data["content_type"],
            text=data.get("text"),
            target_type=target_type,
        ),
        reply_markup=broadcast_confirm_menu,
    )
    try:
        await message.bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=data["source_chat_id"],
            message_id=data["source_message_id"],
        )
    except TelegramAPIError:
        logger.exception("Reklama preview yuborishda Telegram xatosi | admin_id=%s", message.from_user.id)
        await message.answer(
            "Reklama previewini ko'rsatib bo'lmadi. Postni qayta yuboring.",
            reply_markup=broadcast_cancel_menu,
        )
        await state.set_state(BroadcastSendState.waiting_post)


@router.message(BroadcastSendState.confirming)
async def confirm_broadcast_send(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    if message.text != BROADCAST_CONFIRM_BUTTON:
        await message.answer(
            "Yuborish uchun tasdiqlash tugmasini bosing.",
            reply_markup=broadcast_confirm_menu,
        )
        return

    data = await state.get_data()
    await message.answer("Reklama job navbatga qo'yilmoqda...")

    try:
        async with async_session_maker() as session:
            service = _build_broadcast_service(session)
            campaign = await service.prepare_campaign(
                admin_id=message.from_user.id,
                content_type=data["content_type"],
                text=data.get("text"),
                file_id=data.get("file_id"),
                source_chat_id=data["source_chat_id"],
                source_message_id=data["source_message_id"],
                target_type=data["target_type"],
            )
            job = await service.broadcast_repository.create_job(
                campaign_id=campaign.id,
                admin_chat_id=message.chat.id,
            )
    except SQLAlchemyError:
        logger.exception("Reklama yuborishda database xatosi")
        await message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        await state.clear()
        return

    await state.clear()
    await message.answer(
        "📣 <b>Reklama navbatga qo'yildi</b>\n\n"
        f"Campaign ID: <code>{campaign.id}</code>\n"
        f"Job ID: <code>{job.id}</code>\n\n"
        "Yuborish fon rejimida bajariladi. Progress xabarlari shu chatga yuboriladi.",
        reply_markup=broadcast_menu,
    )


@router.message(F.text == BROADCAST_CANCEL_JOB_BUTTON)
async def start_cancel_broadcast_job(message: types.Message, state: FSMContext):
    await state.set_state(BroadcastCancelState.waiting_job_id)
    await message.answer(
        "To'xtatiladigan reklama Job ID raqamini yuboring.",
        reply_markup=broadcast_cancel_menu,
    )


@router.message(BroadcastCancelState.waiting_job_id)
async def finish_cancel_broadcast_job(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    job_id_text = (message.text or "").strip()
    if not job_id_text.isdigit():
        await message.answer("Job ID raqamini yuboring.", reply_markup=broadcast_cancel_menu)
        return

    job_id = int(job_id_text)
    await state.update_data(job_id=job_id)
    await state.set_state(BroadcastCancelState.confirming)
    await message.answer(
        "Ushbu reklama jobini to'xtatishni tasdiqlaysizmi?\n\n"
        f"Job ID: <code>{job_id}</code>",
        reply_markup=broadcast_cancel_job_confirm_inline_keyboard(job_id),
    )


@router.callback_query(
    BroadcastCancelState.confirming,
    F.data.startswith(f"{BROADCAST_CANCEL_JOB_CONFIRM_CALLBACK}:"),
)
async def confirm_cancel_broadcast_job(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    job_id = _callback_id(callback.data)
    if job_id is None:
        await callback.answer("Job ID noto'g'ri.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)

    try:
        async with async_session_maker() as session:
            repository = BroadcastRepository(session)
            updated = await repository.request_cancel_job(job_id)
    except SQLAlchemyError:
        logger.exception("Broadcast job cancel qilishda database xatosi | job_id=%s", job_id)
        if callback.message:
            await callback.message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        await state.clear()
        return

    await state.clear()
    if callback.message:
        await callback.message.answer(
            "Reklamani to'xtatish so'rovi qabul qilindi." if updated else "Bunday active job topilmadi.",
            reply_markup=broadcast_menu,
        )


@router.callback_query(
    BroadcastCancelState.confirming,
    F.data.startswith(f"{BROADCAST_CANCEL_JOB_CANCEL_CALLBACK}:"),
)
async def cancel_cancel_broadcast_job(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Bekor qilindi.")
    await state.clear()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Reklamani to'xtatish bekor qilindi.", reply_markup=broadcast_menu)


@router.message(BroadcastCancelState.confirming)
async def cancel_broadcast_job_text_fallback(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    data = await state.get_data()
    job_id = data.get("job_id")
    if not job_id:
        await state.set_state(BroadcastCancelState.waiting_job_id)
        await message.answer("Job ID raqamini qayta yuboring.", reply_markup=broadcast_cancel_menu)
        return

    await message.answer(
        "To'xtatishni inline tugmalar orqali tasdiqlang.",
        reply_markup=broadcast_cancel_job_confirm_inline_keyboard(job_id),
    )


@router.message(F.text == BROADCAST_DELETE_BUTTON)
async def start_broadcast_delete(message: types.Message, state: FSMContext):
    try:
        async with async_session_maker() as session:
            service = _build_broadcast_service(session)
            text = await service.build_delete_list()
    except SQLAlchemyError:
        logger.exception("Reklamalar ro'yxatini olishda database xatosi")
        await message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        return

    if "topilmadi" in text:
        await message.answer(text, reply_markup=broadcast_menu)
        return

    await state.set_state(BroadcastDeleteState.waiting_campaign_id)
    await message.answer(text, reply_markup=broadcast_cancel_menu)


@router.message(BroadcastDeleteState.waiting_campaign_id)
async def choose_broadcast_delete_campaign(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    campaign_id_text = (message.text or "").strip()
    if not campaign_id_text.isdigit():
        await message.answer("Reklama ID raqamini yuboring.", reply_markup=broadcast_cancel_menu)
        return

    campaign_id = int(campaign_id_text)
    try:
        async with async_session_maker() as session:
            service = _build_broadcast_service(session)
            text = await service.build_campaign_delete_confirm(campaign_id)
    except SQLAlchemyError:
        logger.exception("Reklama ma'lumotini olishda database xatosi")
        await message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        await state.clear()
        return

    if not text:
        await message.answer(
            "Bunday reklama topilmadi yoki allaqachon o'chirilgan.",
            reply_markup=broadcast_menu,
        )
        await state.clear()
        return

    await state.update_data(campaign_id=campaign_id)
    await state.set_state(BroadcastDeleteState.confirming)
    await message.answer(text, reply_markup=broadcast_delete_confirm_inline_keyboard(campaign_id))


@router.callback_query(
    BroadcastDeleteState.confirming,
    F.data.startswith(f"{BROADCAST_DELETE_CONFIRM_CALLBACK}:"),
)
async def confirm_broadcast_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    campaign_id = _callback_id(callback.data)
    if campaign_id is None:
        await callback.answer("Reklama ID noto'g'ri.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Reklama xabarlarini o'chirish boshlandi. Natijani kuting...")

    try:
        async with async_session_maker() as session:
            service = _build_broadcast_service(session)
            campaign = await service.broadcast_repository.get_campaign_by_id(campaign_id)
            if not campaign:
                if callback.message:
                    await callback.message.answer("Reklama topilmadi.", reply_markup=broadcast_menu)
                await state.clear()
                return
            result = await service.delete_campaign_messages(callback.bot, campaign)
    except SQLAlchemyError:
        logger.exception("Reklamani o'chirishda database xatosi")
        if callback.message:
            await callback.message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        await state.clear()
        return

    await state.clear()
    if callback.message:
        await callback.message.answer(
            "🗑 <b>Reklamani o'chirish yakunlandi</b>\n\n"
            f"✅ Userlardan o'chirildi: <b>{result['users']}</b>\n"
            f"✅ Guruhlardan o'chirildi: <b>{result['groups']}</b>\n"
            f"✅ Kanallardan o'chirildi: <b>{result['channels']}</b>\n"
            f"❌ O'chmadi: <b>{result['failed']}</b>",
            reply_markup=broadcast_menu,
        )


@router.callback_query(
    BroadcastDeleteState.confirming,
    F.data.startswith(f"{BROADCAST_DELETE_CANCEL_CALLBACK}:"),
)
async def cancel_broadcast_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Bekor qilindi.")
    await state.clear()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Reklamani o'chirish bekor qilindi.", reply_markup=broadcast_menu)


@router.message(BroadcastDeleteState.confirming)
async def broadcast_delete_text_fallback(message: types.Message, state: FSMContext):
    if await _handle_broadcast_common_buttons(message, state):
        return

    data = await state.get_data()
    campaign_id = data.get("campaign_id")
    if not campaign_id:
        await state.set_state(BroadcastDeleteState.waiting_campaign_id)
        await message.answer("Reklama ID raqamini qayta yuboring.", reply_markup=broadcast_cancel_menu)
        return

    await message.answer(
        "O'chirishni inline tugmalar orqali tasdiqlang.",
        reply_markup=broadcast_delete_confirm_inline_keyboard(campaign_id),
    )


@router.message(F.text == BROADCAST_HISTORY_BUTTON)
async def show_broadcast_history(message: types.Message):
    try:
        async with async_session_maker() as session:
            service = _build_broadcast_service(session)
            text = await service.build_campaign_history()
    except SQLAlchemyError:
        logger.exception("Reklama tarixini olishda database xatosi")
        await message.answer(BROADCAST_ERROR_MESSAGE, reply_markup=broadcast_menu)
        return

    await message.answer(text, reply_markup=broadcast_menu)


@router.message(F.text == BROADCAST_BACK_BUTTON)
async def broadcast_back_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)


@router.message(F.text == BROADCAST_ADMIN_BUTTON)
async def broadcast_admin_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)


def _callback_id(callback_data: str | None) -> int | None:
    if not callback_data:
        return None
    value = callback_data.rsplit(":", 1)[-1]
    if not value.isdigit():
        return None
    return int(value)


async def _handle_broadcast_common_buttons(message: types.Message, state: FSMContext) -> bool:
    if message.text == BROADCAST_CANCEL_BUTTON:
        await state.clear()
        await message.answer("Amal bekor qilindi.", reply_markup=broadcast_menu)
        return True

    if message.text == BROADCAST_ADMIN_BUTTON:
        await state.clear()
        await message.answer("Admin panelga qaytdingiz.", reply_markup=admin_menu)
        return True

    if message.text == BROADCAST_BACK_BUTTON:
        await state.clear()
        await message.answer("Reklama bo'limiga qaytdingiz.", reply_markup=broadcast_menu)
        return True

    return False


def _message_content_type(message: types.Message) -> str:
    content_type = message.content_type
    return content_type.value if hasattr(content_type, "value") else str(content_type)


def _message_file_id(message: types.Message, content_type: str) -> str | None:
    if content_type == "photo" and message.photo:
        return message.photo[-1].file_id
    if content_type == "video" and message.video:
        return message.video.file_id
    if content_type == "document" and message.document:
        return message.document.file_id
    if content_type == "animation" and message.animation:
        return message.animation.file_id
    if content_type == "audio" and message.audio:
        return message.audio.file_id
    if content_type == "voice" and message.voice:
        return message.voice.file_id
    return None
