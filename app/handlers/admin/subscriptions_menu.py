from aiogram import Router, types

from app.filters.admin import AdminFilter
from app.keyboards.admin.reply import admin_menu
from app.keyboards.admin.subscriptions import (
    SUBSCRIPTIONS_ADD_BUTTON,
    SUBSCRIPTIONS_ADD_CHANNEL_BUTTON,
    SUBSCRIPTIONS_ADD_GROUP_BUTTON,
    SUBSCRIPTIONS_ADD_LINK_BUTTON,
    SUBSCRIPTIONS_ADD_MENU_BUTTON,
    SUBSCRIPTIONS_ADMIN_BUTTON,
    SUBSCRIPTIONS_MENU_BUTTON,
    SUBSCRIPTIONS_PANEL_BUTTON,
    add_subscription_menu,
    channel_type_menu,
    group_type_menu,
    link_type_menu,
    subscriptions_menu,
)

router = Router()
router.message.filter(AdminFilter())


@router.message(lambda message: message.text == SUBSCRIPTIONS_PANEL_BUTTON)
async def subscriptions_panel(message: types.Message):
    await message.answer(
        "Majburiy obunalar bo'limi.",
        reply_markup=subscriptions_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADD_BUTTON)
async def add_subscription_menu_handler(message: types.Message):
    await message.answer(
        "Qaysi turdagi obuna qo'shmoqchisiz?",
        reply_markup=add_subscription_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADD_CHANNEL_BUTTON)
async def add_channel_menu_handler(message: types.Message):
    await message.answer(
        "Qanday kanal qo'shmoqchisiz?",
        reply_markup=channel_type_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADD_GROUP_BUTTON)
async def add_group_menu_handler(message: types.Message):
    await message.answer(
        "Qanday guruh qo'shmoqchisiz?",
        reply_markup=group_type_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADD_LINK_BUTTON)
async def add_link_menu_handler(message: types.Message):
    await message.answer(
        "Qanday homiy havola qo'shmoqchisiz?",
        reply_markup=link_type_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADD_MENU_BUTTON)
async def back_to_add_subscription_menu(message: types.Message):
    await message.answer(
        "Qaysi turdagi obuna qo'shmoqchisiz?",
        reply_markup=add_subscription_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_MENU_BUTTON)
async def back_to_subscriptions_menu(message: types.Message):
    await message.answer(
        "Majburiy obunalar bo'limiga qaytdingiz.",
        reply_markup=subscriptions_menu,
    )


@router.message(lambda message: message.text == SUBSCRIPTIONS_ADMIN_BUTTON)
async def back_to_admin_panel(message: types.Message):
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu,
    )
