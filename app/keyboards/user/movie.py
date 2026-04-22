from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, SwitchInlineQueryChosenChat

def movie_share_keyboard(bot_username: str, movie_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do'stlarga ulashish",
                    switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                        query=f"share_{movie_code}",
                        allow_user_chats=True,
                        allow_bot_chats=False,
                        allow_group_chats=True,
                        allow_channel_chats=False,
                    ),
                )
            ]
        ]
    )
