from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

CANCEL_BUTTON = "❌ Bekor qilish"

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=CANCEL_BUTTON)],
    ],
    resize_keyboard=True,
)
