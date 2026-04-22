from aiogram.types import (
    KeyboardButton,
    KeyboardButtonRequestChat,
    ReplyKeyboardMarkup,
)

private_group_request_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="👥 Guruhni tanlash",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1001,
                    chat_is_channel=False,
                    bot_is_member=True,
                    request_title=True,
                ),
            )
        ],
        [KeyboardButton(text="❌ Bekor qilish")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
