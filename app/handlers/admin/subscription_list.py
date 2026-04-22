import math
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_LIST_BUTTON
from app.keyboards.admin.subscription_list_inline import (
    subscription_list_navigation_keyboard,
)
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.utils.db import safe_db_call
from app.utils.text import safe_html

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PAGE_SIZE = 5
logger = logging.getLogger(__name__)


def _build_address_line(sub) -> str:
    if sub.subscription_type in ("public_channel", "public_group"):
        return safe_html(sub.chat_username or "-")

    return f'<a href="{safe_html(sub.invite_link)}">Ochish</a>'


async def build_subscription_list_text(page: int):
    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)

            total_count = await service.count_all_subscriptions()
            if total_count == 0:
                return None, None, None, None, None

            total_pages = math.ceil(total_count / PAGE_SIZE)
            current_page = max(1, min(page, total_pages))
            offset = (current_page - 1) * PAGE_SIZE
            subscriptions = await service.get_paginated_subscriptions(
                limit=PAGE_SIZE,
                offset=offset,
            )
            return subscriptions, current_page, total_pages, offset, total_count

    data = await safe_db_call(
        operation,
        logger=logger,
        context="Obunalar ro'yxatini olish",
    )
    if data is None:
        return "Obunalar ro'yxatini olishda vaqtinchalik xatolik yuz berdi.", None

    subscriptions, page, total_pages, offset, total_count = data
    if total_count == 0:
        return None, None

    subscription_type_labels = {
        "public_channel": "Ommaviy kanal",
        "private_channel": "Maxfiy kanal",
        "public_group": "Ommaviy guruh",
        "private_group": "Maxfiy guruh",
        "external_link": "Homiy havola",
    }

    lines = [f"<b>Obunalar ro'yxati</b>\nSahifa: {page}/{total_pages}\n"]

    for index, sub in enumerate(subscriptions, start=offset + 1):
        status = "Aktiv" if sub.is_active else "Noaktiv"
        subscription_type_label = subscription_type_labels.get(
            sub.subscription_type,
            "Noma'lum",
        )
        lines.append(
            f"{index}. <b>{safe_html(sub.title)}</b>\n"
            f"ID: <code>{sub.id}</code>\n"
            f"Turi: {subscription_type_label}\n"
            f"Manzil: {_build_address_line(sub)}\n"
            f"Holati: {status}\n"
        )

    return "\n".join(lines), subscription_list_navigation_keyboard(page, total_pages)


@router.message(F.text == SUBSCRIPTIONS_LIST_BUTTON)
async def show_subscription_list(message: Message):
    text, keyboard = await build_subscription_list_text(page=1)

    if not text:
        await message.answer("Hozircha obunalar yo'q.")
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith("subscription_list:"))
async def paginate_subscription_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    text, keyboard = await build_subscription_list_text(page=page)

    if not text:
        await callback.answer("Ma'lumot topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()
