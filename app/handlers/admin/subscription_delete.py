import math
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import cancel_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_DELETE_BUTTON
from app.keyboards.admin.subscription_delete_inline import subscription_delete_keyboard
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.states.subscription import DeleteSubscriptionState
from app.utils.callbacks import STALE_CALLBACK_MESSAGE, normalize_offset, normalize_page, parse_callback_int
from app.utils.db import safe_db_call
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)


def build_subscription_type_label(subscription_type: str) -> str:
    type_labels = {
        "public_channel": "Ommaviy kanal",
        "private_channel": "Maxfiy kanal",
        "public_group": "Ommaviy guruh",
        "private_group": "Maxfiy guruh",
        "external_link": "Homiy havola",
    }
    return type_labels.get(subscription_type, "Noma'lum")


def _build_address_line(sub) -> str:
    if sub.subscription_type in ("public_channel", "public_group"):
        return safe_html(sub.chat_username or "-")

    return f'<a href="{safe_html(sub.invite_link)}">Ochish</a>'


async def build_delete_list_text(page: int):
    page = normalize_page(page)

    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)

            total_count = await service.count_all_subscriptions() or 0
            if total_count == 0:
                return None, None, 0, None, None

            total_pages = math.ceil(total_count / PAGE_SIZE)
            current_page = max(1, min(page, total_pages))
            offset = normalize_offset((current_page - 1) * PAGE_SIZE)
            subscriptions = await service.get_paginated_subscriptions(
                limit=PAGE_SIZE,
                offset=offset,
            )
            return subscriptions, current_page, total_pages, offset, total_count

    data = await safe_db_call(
        operation,
        logger=logger,
        context="O'chiriladigan obunalar ro'yxatini olish",
    )
    if data is None:
        return "Obunalar ro'yxatini olishda vaqtinchalik xatolik yuz berdi.", None, 1

    subscriptions, page, total_pages, offset, total_count = data
    subscriptions = list(subscriptions or [])
    page = normalize_page(page)
    offset = normalize_offset(offset)
    if total_count == 0:
        return None, None, 0

    lines = [
        "<b>O'chirish uchun obunani tanlang</b>",
        f"Sahifa: {page}/{total_pages}",
        "",
    ]

    for index, sub in enumerate(subscriptions, start=offset + 1):
        status = "Aktiv" if sub.is_active else "Noaktiv"
        lines.append(
            f"{index}. <b>{safe_html(sub.title)}</b>\n"
            f"ID: <code>{sub.id}</code>\n"
            f"Turi: {build_subscription_type_label(sub.subscription_type)}\n"
            f"Manzil: {_build_address_line(sub)}\n"
            f"Holati: {status}\n"
        )

    keyboard = subscription_delete_keyboard(
        subscriptions=subscriptions,
        page=page,
        total_pages=total_pages,
    )

    return "\n".join(lines), keyboard, page


@router.message(F.text == SUBSCRIPTIONS_DELETE_BUTTON)
async def show_delete_list(message: Message, state: FSMContext):
    text, keyboard, _ = await build_delete_list_text(page=1)

    if not text:
        await state.clear()
        await message.answer("Hozircha obunalar yo'q.")
        return

    await state.set_state(DeleteSubscriptionState.selecting)

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await message.answer(
        "Ortga qaytish uchun '❌ Bekor qilish' tugmasidan foydalaning.",
        reply_markup=cancel_keyboard,
    )


@router.callback_query(
    DeleteSubscriptionState.selecting,
    F.data.startswith("delete_subscription_page:"),
)
async def paginate_delete_list(callback: CallbackQuery):
    page = normalize_page(parse_callback_int(callback.data, 1, default=1))
    text, keyboard, _ = await build_delete_list_text(page=page)

    if not text:
        await callback.answer("Hozircha obunalar yo'q.", show_alert=True)
        await callback.message.edit_text("Hozircha obunalar yo'q.")
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(
    DeleteSubscriptionState.selecting,
    F.data == "delete_subscription_current_page",
)
async def keep_delete_page(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(
    DeleteSubscriptionState.selecting,
    F.data.startswith("delete_subscription:"),
)
async def delete_subscription_handler(callback: CallbackQuery, state: FSMContext):
    subscription_id = parse_callback_int(callback.data, 1)
    page = normalize_page(parse_callback_int(callback.data, 2, default=1))
    if subscription_id is None:
        await callback.answer(STALE_CALLBACK_MESSAGE, show_alert=True)
        return

    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            return await service.delete_subscription(subscription_id)

    deleted = await safe_db_call(
        operation,
        logger=logger,
        context=f"Obunani o'chirish | subscription_id={subscription_id}",
    )
    if deleted is None:
        await callback.answer("Obunani o'chirishda vaqtinchalik xatolik yuz berdi.", show_alert=True)
        return

    if not deleted:
        await callback.answer("Obuna topilmadi.", show_alert=True)
        return

    text, keyboard, actual_page = await build_delete_list_text(page=page)

    if not text:
        await state.clear()
        await callback.message.edit_text("Barcha obunalar o'chirildi.")
        await callback.answer("Obuna o'chirildi.")
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer(f"Obuna o'chirildi. Sahifa: {actual_page}")
