from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def movie_base_navigation_keyboard(
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


def movie_base_selection_keyboard(
    bases,
    page: int,
    total_pages: int,
    callback_prefix: str,
    action_text: str,
) -> InlineKeyboardMarkup:
    keyboard = []

    for movie_base in bases:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{action_text} {movie_base.title[:28]}",
                    callback_data=f"{callback_prefix}:select:{movie_base.id}:{page}",
                )
            ]
        )

    keyboard.append(
        movie_base_navigation_keyboard(page, total_pages, callback_prefix).inline_keyboard[0]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def movie_base_delete_confirmation_keyboard(movie_base_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, o'chirish",
                    callback_data=f"movie_base_delete:confirm:{movie_base_id}:{page}",
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"movie_base_delete:cancel:{page}",
                ),
            ]
        ]
    )
