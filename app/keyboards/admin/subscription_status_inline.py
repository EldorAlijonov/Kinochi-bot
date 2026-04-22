from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_status_keyboard(
    subscriptions,
    page: int,
    total_pages: int,
    callback_prefix: str,
    action_text: str,
) -> InlineKeyboardMarkup:
    keyboard = []

    for sub in subscriptions:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{action_text} {sub.title[:28]}",
                    callback_data=f"{callback_prefix}:select:{sub.id}:{page}",
                )
            ]
        )

    navigation_row = []
    if page > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"{callback_prefix}:page:{page - 1}",
            )
        )

    navigation_row.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data=f"{callback_prefix}:current",
        )
    )

    if page < total_pages:
        navigation_row.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"{callback_prefix}:page:{page + 1}",
            )
        )

    keyboard.append(navigation_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
