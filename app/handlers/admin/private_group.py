from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
import logging

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.private_group_request import private_group_request_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_PRIVATE_GROUP_BUTTON, subscriptions_menu
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.states.subscription import AddPrivateGroupState
from app.utils.checker import validate_bot_for_subscription
from app.utils.chat import get_chat_title
from app.utils.db import safe_db_call
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
logger = logging.getLogger(__name__)


@router.message(F.text == SUBSCRIPTIONS_PRIVATE_GROUP_BUTTON)
async def add_private_group(message: types.Message, state: FSMContext):
    await state.set_state(AddPrivateGroupState.shared_chat)
    await message.answer(
        "Maxfiy guruh qo'shish uchun pastdagi tugma orqali guruhni tanlang.",
        reply_markup=private_group_request_keyboard,
    )


@router.message(AddPrivateGroupState.shared_chat, F.chat_shared)
async def get_private_group_shared_chat(message: types.Message, state: FSMContext):
    chat_shared = message.chat_shared
    await _handle_private_group_chat(
        message=message,
        state=state,
        chat_id=chat_shared.chat_id,
        fallback_title=chat_shared.title or "Nomsiz guruh",
    )


@router.message(AddPrivateGroupState.shared_chat)
async def private_group_expected_chat_shared(message: types.Message, state: FSMContext):
    raw_chat_id = (message.text or "").strip()
    if raw_chat_id.lstrip("-").isdigit():
        await _handle_private_group_chat(
            message=message,
            state=state,
            chat_id=int(raw_chat_id),
            fallback_title="Nomsiz guruh",
        )
        return

    await message.answer(
        "Iltimos, guruhni maxsus tugma orqali tanlang yoki chat ID yuboring.",
        reply_markup=private_group_request_keyboard,
    )


@router.message(AddPrivateGroupState.invite_link, F.text, F.text != CANCEL_BUTTON)
async def save_private_group(message: types.Message, state: FSMContext):
    invite_link = (message.text or "").strip()
    data = await state.get_data()

    title = data.get("title") or "Nomsiz guruh"
    chat_id = data.get("chat_id")

    if not chat_id:
        await state.clear()
        await message.answer(
            "Ma'lumotlar topilmadi. Jarayonni boshidan boshlang.",
            reply_markup=subscriptions_menu,
        )
        return

    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            return await service.create_private_group(
                title=title,
                chat_id=chat_id,
                invite_link=invite_link,
            )

    result = await safe_db_call(
        operation,
        logger=logger,
        context=f"Maxfiy guruhni saqlash | chat_id={chat_id}",
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
        "Maxfiy guruh muvaffaqiyatli qo'shildi.\n\n"
        f"<b>Nomi:</b> {safe_html(subscription.title)}\n"
        f"<b>Chat ID:</b> <code>{subscription.chat_id}</code>\n"
        f"<b>Havola:</b> <a href=\"{safe_html(subscription.invite_link)}\">Guruhga o'tish</a>",
        reply_markup=subscriptions_menu,
    )


async def _handle_private_group_chat(
    message: types.Message,
    state: FSMContext,
    chat_id: int,
    fallback_title: str,
):
    try:
        chat = await message.bot.get_chat(chat_id)
    except TelegramBadRequest:
        await message.answer("Guruh topilmadi yoki bot guruhni ko'ra olmayapti.", reply_markup=private_group_request_keyboard)
        return
    except TelegramAPIError:
        await message.answer("Guruhni tekshirib bo'lmadi. Bot guruhga qo'shilganini tekshiring.", reply_markup=private_group_request_keyboard)
        return

    if chat.type not in ("group", "supergroup"):
        await message.answer("Bu guruh emas. Iltimos, guruhni maxsus tugma orqali tanlang.", reply_markup=private_group_request_keyboard)
        return

    validation = await validate_bot_for_subscription(message.bot, chat_id)
    if not validation.ok:
        await message.answer(
            validation.message,
            reply_markup=private_group_request_keyboard,
        )
        return

    group_title = get_chat_title(chat, fallback_title)
    await state.update_data(chat_id=chat_id, title=group_title)
    await state.set_state(AddPrivateGroupState.invite_link)
    await message.answer(
        "Guruh aniqlandi.\n\n"
        f"<b>Guruh:</b> {safe_html(group_title)}\n"
        f"<b>Chat ID:</b> <code>{chat_id}</code>\n\n"
        "Endi guruh uchun invite link yuboring.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddPrivateGroupState.invite_link)
async def invalid_private_group_invite_input(message: types.Message):
    await message.answer(
        "Iltimos, invite linkni matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )
