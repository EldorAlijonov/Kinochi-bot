from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_list_navigation_keyboard(page: int, total_pages: int):
    buttons = []
    row = []

    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"subscription_list:{page - 1}",
            )
        )

    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"subscription_list:{page + 1}",
            )
        )

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
