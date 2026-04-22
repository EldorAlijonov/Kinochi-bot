from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BROADCAST_PANEL_BUTTON = "📣 Reklama"
BROADCAST_SEND_BUTTON = "📤 Reklama yuborish"
BROADCAST_DELETE_BUTTON = "🗑 Reklamani o'chirish"
BROADCAST_HISTORY_BUTTON = "📋 Reklamalar tarixi"
BROADCAST_CANCEL_JOB_BUTTON = "⏹ Reklamani to'xtatish"
BROADCAST_BACK_BUTTON = "🔙 Ortga qaytish"
BROADCAST_ADMIN_BUTTON = "🛠 Admin panel"
BROADCAST_CANCEL_BUTTON = "❌ Bekor qilish"

BROADCAST_USERS_BUTTON = "👥 Foydalanuvchilarga"
BROADCAST_GROUPS_BUTTON = "👥 Guruhlarga"
BROADCAST_CHANNELS_BUTTON = "📢 Kanallarga"
BROADCAST_ALL_BUTTON = "🌐 Barchasiga"
BROADCAST_CONFIRM_BUTTON = "✅ Yuborishni tasdiqlash"

BROADCAST_DELETE_CONFIRM_CALLBACK = "broadcast_delete:confirm"
BROADCAST_DELETE_CANCEL_CALLBACK = "broadcast_delete:cancel"
BROADCAST_CANCEL_JOB_CONFIRM_CALLBACK = "broadcast_cancel:confirm"
BROADCAST_CANCEL_JOB_CANCEL_CALLBACK = "broadcast_cancel:cancel"

broadcast_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BROADCAST_SEND_BUTTON)],
        [
            KeyboardButton(text=BROADCAST_DELETE_BUTTON),
            KeyboardButton(text=BROADCAST_HISTORY_BUTTON),
        ],
        [KeyboardButton(text=BROADCAST_CANCEL_JOB_BUTTON)],
        [
            KeyboardButton(text=BROADCAST_BACK_BUTTON),
            KeyboardButton(text=BROADCAST_ADMIN_BUTTON),
        ],
    ],
    resize_keyboard=True,
)

broadcast_cancel_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BROADCAST_CANCEL_BUTTON)],
        [KeyboardButton(text=BROADCAST_ADMIN_BUTTON)],
    ],
    resize_keyboard=True,
)

broadcast_target_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=BROADCAST_USERS_BUTTON),
            KeyboardButton(text=BROADCAST_GROUPS_BUTTON),
        ],
        [
            KeyboardButton(text=BROADCAST_CHANNELS_BUTTON),
            KeyboardButton(text=BROADCAST_ALL_BUTTON),
        ],
        [KeyboardButton(text=BROADCAST_CANCEL_BUTTON)],
    ],
    resize_keyboard=True,
)

broadcast_confirm_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BROADCAST_CONFIRM_BUTTON)],
        [KeyboardButton(text=BROADCAST_CANCEL_BUTTON)],
    ],
    resize_keyboard=True,
)

def broadcast_delete_confirm_inline_keyboard(campaign_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Barchasidan o'chirish",
                    callback_data=f"{BROADCAST_DELETE_CONFIRM_CALLBACK}:{campaign_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"{BROADCAST_DELETE_CANCEL_CALLBACK}:{campaign_id}",
                )
            ],
        ]
    )


def broadcast_cancel_job_confirm_inline_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏹ To'xtatishni tasdiqlash",
                    callback_data=f"{BROADCAST_CANCEL_JOB_CONFIRM_CALLBACK}:{job_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"{BROADCAST_CANCEL_JOB_CANCEL_CALLBACK}:{job_id}",
                )
            ],
        ]
    )
