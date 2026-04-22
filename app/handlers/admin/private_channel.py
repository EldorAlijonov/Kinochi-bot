from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_PRIVATE_CHANNEL_BUTTON, subscriptions_menu
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.states.subscription import AddPrivateChannelState
from app.utils.checker import validate_bot_for_subscription
from app.utils.chat import extract_forwarded_chat, get_chat_title
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
logger = logging.getLogger(__name__)
PRIVATE_CHANNEL_DB_ERROR_MESSAGE = (
    "Maxfiy kanalni saqlashda vaqtinchalik database xatosi yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
)


@router.message(F.text == SUBSCRIPTIONS_PRIVATE_CHANNEL_BUTTON)
async def add_private_channel(message: types.Message, state: FSMContext):
    await state.set_state(AddPrivateChannelState.forwarded_post)
    await message.answer(
        "Maxfiy kanal qo'shish uchun botni kanalga admin qiling va shu kanaldan istalgan postni forward qiling.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateChannelState.forwarded_post, F.text != CANCEL_BUTTON)
async def get_private_channel_forwarded_post(message: types.Message, state: FSMContext):
    forwarded_chat = extract_forwarded_chat(message)
    chat_id = forwarded_chat.id if forwarded_chat else None
    raw_chat_id = (message.text or "").strip()

    if chat_id is None and raw_chat_id.lstrip("-").isdigit():
        chat_id = int(raw_chat_id)

    if chat_id is None:
        await message.answer(
            "Kanalni aniqlab bo'lmadi. Maxfiy kanaldan forward qilingan post yoki chat ID yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    try:
        chat = await message.bot.get_chat(chat_id)
    except TelegramBadRequest:
        await message.answer("Kanal topilmadi yoki bot kanalni ko'ra olmayapti.", reply_markup=cancel_keyboard)
        return
    except TelegramAPIError:
        await message.answer("Kanalni tekshirib bo'lmadi. Bot kanalga qo'shilganini tekshiring.", reply_markup=cancel_keyboard)
        return

    if chat.type != "channel":
        await message.answer("Bu kanal emas. Iltimos, maxfiy kanaldan forward qilingan post yuboring.", reply_markup=cancel_keyboard)
        return

    if chat.username:
        await message.answer(
            "Bu ommaviy kanal ko'rinmoqda. Uni 'Ommaviy kanal' orqali qo'shing.",
            reply_markup=cancel_keyboard,
        )
        return

    validation = await validate_bot_for_subscription(message.bot, chat_id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=cancel_keyboard,
        )
        return

    title = get_chat_title(chat, get_chat_title(forwarded_chat, "Nomsiz kanal") if forwarded_chat else "Nomsiz kanal")
    await state.update_data(chat_id=chat_id, title=title)
    await state.set_state(AddPrivateChannelState.invite_link)
    await message.answer(
        "Kanal aniqlandi.\n\n"
        f"<b>Nomi:</b> {safe_html(title)}\n"
        f"<b>Chat ID:</b> <code>{chat_id}</code>\n\n"
        "Endi maxfiy kanal uchun invite link yuboring.\n"
        "Masalan: <code>https://t.me/+abc123xyz</code>",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateChannelState.invite_link, F.text, F.text != CANCEL_BUTTON)
async def get_private_channel_invite_link(message: types.Message, state: FSMContext):
    invite_link = (message.text or "").strip()
    data = await state.get_data()

    title = data.get("title") or "Nomsiz kanal"
    chat_id = data.get("chat_id")

    if not chat_id:
        await state.clear()
        await message.answer(
            "Ma'lumotlar topilmadi. Jarayonni boshidan boshlang.",
            reply_markup=subscriptions_menu,
        )
        return

    try:
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            result = await service.create_private_channel(
                title=title,
                chat_id=chat_id,
                invite_link=invite_link,
            )
    except SQLAlchemyError:
        logger.exception("Maxfiy kanalni saqlashda database xatosi | chat_id=%s", chat_id)
        await message.answer(PRIVATE_CHANNEL_DB_ERROR_MESSAGE, reply_markup=cancel_keyboard)
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    subscription = result["subscription"]
    await state.clear()
    await message.answer(
        "Maxfiy kanal muvaffaqiyatli qo'shildi.\n\n"
        f"<b>Nomi:</b> {safe_html(subscription.title)}\n"
        f"<b>Chat ID:</b> <code>{subscription.chat_id}</code>\n"
        f"<b>Havola:</b> <a href=\"{safe_html(subscription.invite_link)}\">Kanalga o'tish</a>",
        reply_markup=subscriptions_menu,
    )


@router.message(AddPrivateChannelState.invite_link)
async def invalid_private_channel_invite_input(message: types.Message):
    await message.answer(
        "Iltimos, invite linkni matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )
