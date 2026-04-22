from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.keyboards.admin.broadcast import BROADCAST_PANEL_BUTTON
from app.keyboards.admin.movies import MOVIES_PANEL_BUTTON
from app.keyboards.admin.statistics import STATISTICS_PANEL_BUTTON
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_PANEL_BUTTON
from app.keyboards.admin.users import USERS_PANEL_BUTTON

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=SUBSCRIPTIONS_PANEL_BUTTON),
            KeyboardButton(text=MOVIES_PANEL_BUTTON),
        ],
        [
            KeyboardButton(text=STATISTICS_PANEL_BUTTON),
            KeyboardButton(text=USERS_PANEL_BUTTON),
        ],
        [
            KeyboardButton(text=BROADCAST_PANEL_BUTTON),
        ],
    ],
    resize_keyboard=True,
)
