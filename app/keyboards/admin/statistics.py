from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

STATISTICS_PANEL_BUTTON = "📊 Statistika"
STATISTICS_GENERAL_BUTTON = "📊 Umumiy statistika"
STATISTICS_USER_ACTIVITY_BUTTON = "👥 Foydalanuvchi faolligi"
STATISTICS_MOVIE_BUTTON = "🎬 Kino statistikasi"
STATISTICS_SUBSCRIPTION_BUTTON = "📢 Obuna statistikasi"
STATISTICS_TOP_MOVIES_BUTTON = "🔥 Top kinolar"
STATISTICS_BASE_BUTTON = "🗂 Baza statistikasi"
STATISTICS_REFRESH_BUTTON = "🔄 Yangilash"
STATISTICS_BACK_BUTTON = "🔙 Ortga qaytish"
STATISTICS_ADMIN_BUTTON = "🛠 Admin panel"

statistics_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=STATISTICS_GENERAL_BUTTON),
            KeyboardButton(text=STATISTICS_USER_ACTIVITY_BUTTON),
        ],
        [
            KeyboardButton(text=STATISTICS_MOVIE_BUTTON),
            KeyboardButton(text=STATISTICS_SUBSCRIPTION_BUTTON),
        ],
        [
            KeyboardButton(text=STATISTICS_TOP_MOVIES_BUTTON),
            KeyboardButton(text=STATISTICS_BASE_BUTTON),
        ],
        [
            KeyboardButton(text=STATISTICS_REFRESH_BUTTON),
        ],
        [
            KeyboardButton(text=STATISTICS_BACK_BUTTON),
            KeyboardButton(text=STATISTICS_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)
