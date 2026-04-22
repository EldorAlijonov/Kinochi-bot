from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MOVIES_PANEL_BUTTON = "🎬 Kinolar bazasi"
MOVIES_ADD_BASE_BUTTON = "🗂 Baza qo'shish"
MOVIES_LIST_BUTTON = "📋 Bazalar ro'yxati"
MOVIES_SAVED_LIST_BUTTON = "🎞 Saqlangan kinolar"
MOVIES_DELETE_MOVIE_BUTTON = "🗑 Kinoni o'chirish"
MOVIES_DELETE_BUTTON = "🗑 Bazani o'chirish"
MOVIES_ACTIVATE_BASE_BUTTON = "✅ Bazani aktiv qilish"
MOVIES_DEACTIVATE_BASE_BUTTON = "⛔ Bazani noaktiv qilish"
MOVIES_UPLOAD_BUTTON = "📥 Kino yuklash"
MOVIES_PUBLIC_BASE_BUTTON = "📢 Ommaviy kanal qo'shish"
MOVIES_PRIVATE_BASE_BUTTON = "🔒 Maxfiy kanal qo'shish"
MOVIES_BACK_BUTTON = "🔙 Ortga qaytish"
MOVIES_ADMIN_BUTTON = "🛠 Admin panel"
MOVIES_DELETE_CANCEL_BUTTON = "❌ Bekor qilish"

movies_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=MOVIES_ADD_BASE_BUTTON),
            KeyboardButton(text=MOVIES_LIST_BUTTON),
        ],
        [
            KeyboardButton(text=MOVIES_DELETE_BUTTON),
            KeyboardButton(text=MOVIES_UPLOAD_BUTTON),
        ],
        [
            KeyboardButton(text=MOVIES_SAVED_LIST_BUTTON),
            KeyboardButton(text=MOVIES_DELETE_MOVIE_BUTTON),
        ],
        [
            KeyboardButton(text=MOVIES_ACTIVATE_BASE_BUTTON),
            KeyboardButton(text=MOVIES_DEACTIVATE_BASE_BUTTON),
        ],
        [
            KeyboardButton(text=MOVIES_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

movie_base_add_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=MOVIES_PUBLIC_BASE_BUTTON),
            KeyboardButton(text=MOVIES_PRIVATE_BASE_BUTTON),
        ],
        [
            KeyboardButton(text=MOVIES_BACK_BUTTON),
            KeyboardButton(text=MOVIES_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

movie_delete_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=MOVIES_DELETE_CANCEL_BUTTON)],
        [KeyboardButton(text=MOVIES_ADMIN_BUTTON)],
    ],
    resize_keyboard=True,
)
