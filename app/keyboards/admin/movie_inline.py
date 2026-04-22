from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def movie_navigation_keyboard(
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


def movie_list_keyboard(
    movies,
    page: int,
    total_pages: int,
    navigation_callback_prefix: str = "movie_list",
) -> InlineKeyboardMarkup:
    keyboard = []

    for movie, _movie_base in movies:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 O'chirish: {movie.code}",
                    callback_data=f"movie_delete:select:{movie.code}:{page}",
                )
            ]
        )

    keyboard.append(
        movie_navigation_keyboard(
            page=page,
            total_pages=total_pages,
            callback_prefix=navigation_callback_prefix,
        ).inline_keyboard[0]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def movie_delete_options_keyboard(code: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Faqat botdan o'chirish",
                    callback_data=f"movie_delete:db:{code}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Kanaldan ham o'chirish",
                    callback_data=f"movie_delete:channel:{code}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"movie_delete:cancel:{page}",
                )
            ],
        ]
    )
