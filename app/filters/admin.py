from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import ADMINS


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            user = getattr(event, "from_user", None)

        return bool(user and user.id in ADMINS)
