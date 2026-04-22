from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_delete_keyboard(subscriptions, page: int, total_pages: int):
    keyboard = []

    for sub in subscriptions:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 O'chirish: {sub.title[:24]}",
                    callback_data=f"delete_subscription:{sub.id}:{page}",
                )
            ]
        )

    navigation_row = []

    if page > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"delete_subscription_page:{page - 1}",
            )
        )

    navigation_row.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="delete_subscription_current_page",
        )
    )

    if page < total_pages:
        navigation_row.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"delete_subscription_page:{page + 1}",
            )
        )

    if navigation_row:
        keyboard.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
