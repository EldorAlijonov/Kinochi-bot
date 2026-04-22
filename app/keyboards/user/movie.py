from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, SwitchInlineQueryChosenChat

from app.utils.share_text import build_share_link

def movie_share_keyboard(bot_username: str, movie_code: str) -> InlineKeyboardMarkup:
    share_link = build_share_link(bot_username, movie_code)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do'stlarga ulashish",
                    switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                        query=share_link,
                        allow_user_chats=True,
                        allow_bot_chats=False,
                        allow_group_chats=True,
                        allow_channel_chats=False,
                    ),
                )
            ]
        ]
    )
