from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def users_navigation_keyboard(
    page: int,
    total_pages: int,
    callback_prefix: str,
) -> InlineKeyboardMarkup:
    row = []
    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"{callback_prefix}:page:{page - 1}",
            )
        )

    row.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data=f"{callback_prefix}:current",
        )
    )

    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"{callback_prefix}:page:{page + 1}",
            )
        )

    return InlineKeyboardMarkup(inline_keyboard=[row])
