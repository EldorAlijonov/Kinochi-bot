from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

USERS_PANEL_BUTTON = "👥 Foydalanuvchilar"
USERS_TOTAL_BUTTON = "🔢 Jami foydalanuvchilar"
USERS_SEARCH_BUTTON = "🔍 Foydalanuvchi qidirish"
USERS_ACTIVE_BUTTON = "🟢 Aktiv foydalanuvchilar"
USERS_INACTIVE_BUTTON = "🔴 Noaktiv foydalanuvchilar"
USERS_BAN_BUTTON = "🚫 Ban qilish"
USERS_UNBAN_BUTTON = "✅ Bandan chiqarish"
USERS_BROADCAST_BUTTON = "📣 Reklama"
USERS_BACK_BUTTON = "🔙 Ortga qaytish"
USERS_ADMIN_BUTTON = "🛠 Admin panel"
USERS_CANCEL_BUTTON = "❌ Bekor qilish"

BROADCAST_ALL_BUTTON = "👥 Barcha userlar"
BROADCAST_ACTIVE_BUTTON = "🟢 Aktiv userlar"
BROADCAST_INACTIVE_BUTTON = "🔴 Noaktiv userlar"

users_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=USERS_TOTAL_BUTTON),
            KeyboardButton(text=USERS_SEARCH_BUTTON),
        ],
        [
            KeyboardButton(text=USERS_ACTIVE_BUTTON),
            KeyboardButton(text=USERS_INACTIVE_BUTTON),
        ],
        [
            KeyboardButton(text=USERS_BAN_BUTTON),
            KeyboardButton(text=USERS_UNBAN_BUTTON),
        ],
        [
            KeyboardButton(text=USERS_BROADCAST_BUTTON),
        ],
        [
            KeyboardButton(text=USERS_BACK_BUTTON),
            KeyboardButton(text=USERS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

users_cancel_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=USERS_CANCEL_BUTTON)],
        [KeyboardButton(text=USERS_ADMIN_BUTTON)],
    ],
    resize_keyboard=True,
)

broadcast_audience_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=BROADCAST_ALL_BUTTON),
            KeyboardButton(text=BROADCAST_ACTIVE_BUTTON),
        ],
        [
            KeyboardButton(text=BROADCAST_INACTIVE_BUTTON),
        ],
        [
            KeyboardButton(text=USERS_CANCEL_BUTTON),
            KeyboardButton(text=USERS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)
