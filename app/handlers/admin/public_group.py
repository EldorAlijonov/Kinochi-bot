from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
import logging

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_PUBLIC_GROUP_BUTTON, subscriptions_menu
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.services.subscription_validator import parse_username_or_link
from app.states.subscription import AddPublicGroupState
from app.utils.checker import validate_bot_for_subscription
from app.utils.chat import extract_forwarded_chat, get_chat_title
from app.utils.db import safe_db_call
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
logger = logging.getLogger(__name__)


@router.message(F.text == SUBSCRIPTIONS_PUBLIC_GROUP_BUTTON)
async def add_public_group(message: types.Message, state: FSMContext):
    await state.set_state(AddPublicGroupState.username_or_link)
    await message.answer(
        "Ommaviy guruh username yoki havolasini yuboring.\n\n"
        "Masalan:\n<code>@mygroup</code>\n"
        "yoki\n<code>https://t.me/mygroup</code>",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPublicGroupState.username_or_link, F.text, F.text != CANCEL_BUTTON)
async def get_public_group(message: types.Message, state: FSMContext):
    await _save_public_group(message, state, (message.text or "").strip())


@router.message(AddPublicGroupState.username_or_link)
async def get_public_group_forward(message: types.Message, state: FSMContext):
    forwarded_chat = extract_forwarded_chat(message)
    username = getattr(forwarded_chat, "username", None)
    if not username:
        await message.answer(
            "Iltimos, guruh username/linkini yuboring yoki ommaviy guruhdan forward qilingan xabar yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    await _save_public_group(message, state, f"@{username}")


async def _save_public_group(message: types.Message, state: FSMContext, raw_value: str):

    username, _ = parse_username_or_link(raw_value)
    if not username:
        await message.answer(
            "Ommaviy guruh uchun to'g'ri username yoki link yuboring.",
            reply_markup=cancel_keyboard,
        )
        return

    try:
        chat = await message.bot.get_chat(username)
    except TelegramBadRequest:
        await message.answer("Guruh topilmadi. Username yoki linkni tekshiring.", reply_markup=cancel_keyboard)
        return
    except TelegramAPIError:
        await message.answer("Guruhni tekshirib bo'lmadi. Bot guruhga qo'shilganini tekshiring.", reply_markup=cancel_keyboard)
        return

    if chat.type not in ("group", "supergroup"):
        await message.answer("Bu guruh emas. Iltimos, guruh username yoki linkini yuboring.", reply_markup=cancel_keyboard)
        return

    validation = await validate_bot_for_subscription(message.bot, chat.id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=cancel_keyboard,
        )
        return

    title = get_chat_title(chat, "Nomsiz guruh")
    async def operation():
        async with async_session_maker() as session:
            service = SubscriptionService(SubscriptionRepository(session))
            return await service.create_public_group(title=title, raw_value=raw_value)

    result = await safe_db_call(
        operation,
        logger=logger,
        context=f"Ommaviy guruhni saqlash | username={username}",
    )
    if result is None:
        await message.answer(
            "Guruhni saqlashda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            reply_markup=cancel_keyboard,
        )
        return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    subscription = result["subscription"]
    await state.clear()
    await message.answer(
        "Ommaviy guruh muvaffaqiyatli qo'shildi.\n\n"
        f"<b>Nomi:</b> {safe_html(subscription.title)}\n"
        f"<b>Username:</b> {safe_html(subscription.chat_username)}\n"
        f"<b>Havola:</b> {safe_html(subscription.invite_link)}",
        reply_markup=subscriptions_menu,
    )
