from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SUBSCRIPTIONS_PANEL_BUTTON = "📢 Majburiy obunalar"
SUBSCRIPTIONS_ADD_BUTTON = "➕ Obuna qo'shish"
SUBSCRIPTIONS_LIST_BUTTON = "📋 Obunalar ro'yxati"
SUBSCRIPTIONS_DELETE_BUTTON = "🗑 O'chirish"
SUBSCRIPTIONS_ACTIVATE_BUTTON = "✅ Obunani aktiv qilish"
SUBSCRIPTIONS_DEACTIVATE_BUTTON = "⛔ Obunani noaktiv qilish"
SUBSCRIPTIONS_ADMIN_BUTTON = "🛠 Admin panel"

SUBSCRIPTIONS_ADD_CHANNEL_BUTTON = "📢 Kanal qo'shish"
SUBSCRIPTIONS_ADD_GROUP_BUTTON = "👥 Guruh qo'shish"
SUBSCRIPTIONS_ADD_LINK_BUTTON = "🔗 Homiy havola qo'shish"
SUBSCRIPTIONS_MENU_BUTTON = "📢 Obunalar menyusi"
SUBSCRIPTIONS_ADD_MENU_BUTTON = "➕ Qo'shish menyusi"

SUBSCRIPTIONS_PUBLIC_CHANNEL_BUTTON = "📢 Ommaviy kanal"
SUBSCRIPTIONS_PRIVATE_CHANNEL_BUTTON = "🔒 Maxfiy kanal"
SUBSCRIPTIONS_PUBLIC_GROUP_BUTTON = "👥 Ommaviy guruh"
SUBSCRIPTIONS_PRIVATE_GROUP_BUTTON = "🔐 Maxfiy guruh"
SUBSCRIPTIONS_EXTERNAL_LINK_BUTTON = "🔗 Homiy havola"

subscriptions_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=SUBSCRIPTIONS_ADD_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_LIST_BUTTON),
        ],
        [KeyboardButton(text=SUBSCRIPTIONS_DELETE_BUTTON)],
        [
            KeyboardButton(text=SUBSCRIPTIONS_ACTIVATE_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_DEACTIVATE_BUTTON),
        ],
        [KeyboardButton(text=SUBSCRIPTIONS_ADMIN_BUTTON)],
    ],
    resize_keyboard=True,
)

add_subscription_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=SUBSCRIPTIONS_ADD_CHANNEL_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_ADD_GROUP_BUTTON),
        ],
        [KeyboardButton(text=SUBSCRIPTIONS_ADD_LINK_BUTTON)],
        [
            KeyboardButton(text=SUBSCRIPTIONS_MENU_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

channel_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=SUBSCRIPTIONS_PUBLIC_CHANNEL_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_PRIVATE_CHANNEL_BUTTON),
        ],
        [
            KeyboardButton(text=SUBSCRIPTIONS_ADD_MENU_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

group_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=SUBSCRIPTIONS_PUBLIC_GROUP_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_PRIVATE_GROUP_BUTTON),
        ],
        [
            KeyboardButton(text=SUBSCRIPTIONS_ADD_MENU_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

link_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=SUBSCRIPTIONS_EXTERNAL_LINK_BUTTON)],
        [
            KeyboardButton(text=SUBSCRIPTIONS_ADD_MENU_BUTTON),
            KeyboardButton(text=SUBSCRIPTIONS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)
