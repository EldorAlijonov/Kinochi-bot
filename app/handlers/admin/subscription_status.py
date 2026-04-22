import math
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.subscription_status_inline import subscription_status_keyboard
from app.keyboards.admin.subscriptions import (
    SUBSCRIPTIONS_ACTIVATE_BUTTON,
    SUBSCRIPTIONS_DEACTIVATE_BUTTON,
    subscriptions_menu,
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


def _normalize_page(page) -> int:
    try:
        return max(1, int(page or 1))
    except (TypeError, ValueError):
        return 1


def _normalize_offset(offset) -> int:
    try:
        return max(0, int(offset or 0))
    except (TypeError, ValueError):
        return 0


def _parse_status_select_callback(callback_data: str) -> tuple[int | None, int]:
    parts = (callback_data or "").split(":")
    subscription_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
    page = _normalize_page(parts[3] if len(parts) > 3 else 1)
    return subscription_id, page


def _parse_status_page_callback(callback_data: str) -> int:
    parts = (callback_data or "").split(":")
    return _normalize_page(parts[2] if len(parts) > 2 else 1)


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
        username = sub.chat_username or "-"
        if username != "-" and not username.startswith("@"):
            username = f"@{username}"
        return safe_html(username)

    return f'<a href="{safe_html(sub.invite_link)}">Ochish</a>'


async def build_subscription_status_list(page: int, target_active: bool):
    page = _normalize_page(page)

    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            source_active = not target_active
            total_count = await service.count_subscriptions_by_status(source_active)

            if total_count == 0:
                return None, None, 0, None, None

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            current_page = max(1, min(page, total_pages))
            offset = (current_page - 1) * PAGE_SIZE
            subscriptions = await service.get_paginated_subscriptions_by_status(
                is_active=source_active,
                limit=PAGE_SIZE,
                offset=offset,
            )
            return subscriptions, current_page, total_pages, offset, total_count

    data = await safe_db_call(
        operation,
        logger=logger,
        context="Obuna status ro'yxatini olish",
    )
    if data is None:
        return "Obuna ro'yxatini olishda vaqtinchalik xatolik yuz berdi.", None, 1

    subscriptions, page, total_pages, offset, total_count = data
    subscriptions = list(subscriptions or [])
    page = _normalize_page(page)
    offset = _normalize_offset(offset)
    if total_count == 0 or not subscriptions:
        return "Obunalar topilmadi.", None, page

    action_text = "aktiv qilish" if target_active else "noaktiv qilish"
    status_text = "Noaktiv" if target_active else "Aktiv"
    lines = [
        f"<b>{action_text.capitalize()} uchun obunani tanlang</b>",
        f"Sahifa: {page}/{total_pages}",
        f"Ko'rsatilayotgan holat: {status_text}",
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

    callback_prefix = "subscription_activate" if target_active else "subscription_deactivate"
    keyboard = subscription_status_keyboard(
        subscriptions=subscriptions,
        page=page,
        total_pages=total_pages,
        callback_prefix=callback_prefix,
        action_text="✅" if target_active else "❌",
    )
    return "\n".join(lines), keyboard, page


@router.message(F.text == SUBSCRIPTIONS_ACTIVATE_BUTTON)
async def show_inactive_subscriptions(message: Message):
    text, keyboard, _ = await build_subscription_status_list(page=1, target_active=True)
    if not text:
        await message.answer("Aktiv qilinadigan noaktiv obuna yo'q.", reply_markup=subscriptions_menu)
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.message(F.text == SUBSCRIPTIONS_DEACTIVATE_BUTTON)
async def show_active_subscriptions(message: Message):
    text, keyboard, _ = await build_subscription_status_list(page=1, target_active=False)
    if not text:
        await message.answer("Noaktiv qilinadigan aktiv obuna yo'q.", reply_markup=subscriptions_menu)
        return

    await message.answer(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith("subscription_activate:page:"))
async def paginate_inactive_subscriptions(callback: CallbackQuery):
    page = _parse_status_page_callback(callback.data)
    text, keyboard, _ = await build_subscription_status_list(page=page, target_active=True)
    if not text:
        await callback.answer("Aktiv qilinadigan obuna yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("subscription_deactivate:page:"))
async def paginate_active_subscriptions(callback: CallbackQuery):
    page = _parse_status_page_callback(callback.data)
    text, keyboard, _ = await build_subscription_status_list(page=page, target_active=False)
    if not text:
        await callback.answer("Noaktiv qilinadigan obuna yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription_activate:current")
@router.callback_query(F.data == "subscription_deactivate:current")
async def keep_subscription_status_page(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("subscription_activate:select:"))
async def activate_subscription(callback: CallbackQuery):
    subscription_id, page = _parse_status_select_callback(callback.data)
    if subscription_id is None:
        await callback.answer("Callback ma'lumoti noto'g'ri.", show_alert=True)
        return

    await _set_subscription_status(
        callback,
        subscription_id=subscription_id,
        page=page,
        target_active=True,
    )


@router.callback_query(F.data.startswith("subscription_deactivate:select:"))
async def deactivate_subscription(callback: CallbackQuery):
    subscription_id, page = _parse_status_select_callback(callback.data)
    if subscription_id is None:
        await callback.answer("Callback ma'lumoti noto'g'ri.", show_alert=True)
        return

    await _set_subscription_status(
        callback,
        subscription_id=subscription_id,
        page=page,
        target_active=False,
    )


async def _set_subscription_status(
    callback: CallbackQuery,
    subscription_id: int,
    page: int,
    target_active: bool,
):
    page = _normalize_page(page)

    async def operation():
        async with async_session_maker() as session:
            repository = SubscriptionRepository(session)
            service = SubscriptionService(repository)
            return (
                await service.activate_subscription(subscription_id)
                if target_active
                else await service.deactivate_subscription(subscription_id)
            )

    result = await safe_db_call(
        operation,
        logger=logger,
        context=f"Obuna statusini o'zgartirish | subscription_id={subscription_id}",
    )
    if result is None:
        await callback.answer("Obuna statusini o'zgartirishda vaqtinchalik xatolik yuz berdi.", show_alert=True)
        return

    if not result["ok"]:
        await callback.answer(result["message"], show_alert=True)
        return

    text, keyboard, _ = await build_subscription_status_list(
        page=page,
        target_active=target_active,
    )
    if not text:
        await callback.message.edit_text(result["message"])
        await callback.answer(result["message"])
        return

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await callback.answer(result["message"])
