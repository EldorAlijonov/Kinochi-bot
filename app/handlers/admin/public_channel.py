from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_PUBLIC_CHANNEL_BUTTON, subscriptions_menu
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.services.subscription_validator import parse_username_or_link
from app.states.subscription import AddPublicChannelState
from app.utils.checker import validate_bot_for_subscription
from app.utils.chat import extract_forwarded_chat, get_chat_title
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
logger = logging.getLogger(__name__)
PUBLIC_CHANNEL_DB_ERROR_MESSAGE = (
    "Kanalni saqlashda vaqtinchalik database xatosi yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
)


@router.message(F.text == SUBSCRIPTIONS_PUBLIC_CHANNEL_BUTTON)
async def add_public_channel(message: types.Message, state: FSMContext):
    await state.set_state(AddPublicChannelState.username_or_link)
    await message.answer(
        "Ommaviy kanal username yoki havolasini yuboring.\n\n"
        "Masalan:\n<code>@mychannel</code>\n"
        "yoki\n<code>https://t.me/mychannel</code>",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPublicChannelState.username_or_link, F.text, F.text != CANCEL_BUTTON)
async def get_public_channel_username_or_link(message: types.Message, state: FSMContext):
    await _save_public_channel(message, state, (message.text or "").strip())


@router.message(AddPublicChannelState.username_or_link)
async def get_public_channel_forward(message: types.Message, state: FSMContext):
    forwarded_chat = extract_forwarded_chat(message)
    username = getattr(forwarded_chat, "username", None)
    if not username:
        await message.answer(
            "Iltimos, kanal username/linkini yuboring yoki ommaviy kanaldan forward qilingan post yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    await _save_public_channel(message, state, f"@{username}")


async def _save_public_channel(message: types.Message, state: FSMContext, raw_value: str):

    username, _ = parse_username_or_link(raw_value)
    if not username:
        await message.answer(
            "Ommaviy kanal uchun to'g'ri username yoki link yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    try:
        chat = await message.bot.get_chat(username)
    except TelegramBadRequest:
        await message.answer("Kanal topilmadi. Username yoki linkni tekshiring.", reply_markup=cancel_keyboard)
        return
    except TelegramAPIError:
        await message.answer("Kanalni tekshirib bo'lmadi. Bot kanalga qo'shilganini tekshiring.", reply_markup=cancel_keyboard)
        return

    if chat.type != "channel":
        await message.answer("Bu kanal emas. Iltimos, kanal username yoki linkini yuboring.", reply_markup=cancel_keyboard)
        return

    validation = await validate_bot_for_subscription(message.bot, chat.id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=cancel_keyboard,
        )
        return

    title = get_chat_title(chat, "Nomsiz kanal")
    try:
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            result = await service.create_public_channel(title=title, raw_value=raw_value)
    except SQLAlchemyError:
        logger.exception("Ommaviy kanalni saqlashda database xatosi | username=%s", username)
        await message.answer(PUBLIC_CHANNEL_DB_ERROR_MESSAGE, reply_markup=cancel_keyboard)
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    subscription = result["subscription"]
    await state.clear()
    await message.answer(
        "Ommaviy kanal muvaffaqiyatli qo'shildi.\n\n"
        f"<b>Nomi:</b> {safe_html(subscription.title)}\n"
        f"<b>Username:</b> {safe_html(subscription.chat_username)}\n"
        f"<b>Havola:</b> {safe_html(subscription.invite_link)}",
        reply_markup=subscriptions_menu,
    )
