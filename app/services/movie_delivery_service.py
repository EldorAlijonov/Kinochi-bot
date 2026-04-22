import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.exc import SQLAlchemyError

from app.keyboards.user.movie import movie_share_keyboard
from app.utils.movie_title import build_user_movie_caption


class MovieDeliveryService:
    def __init__(self, movie_repository):
        self.movie_repository = movie_repository

    @staticmethod
    async def send_protected_movie_to_user(
        bot,
        chat_id: int,
        movie,
        caption: str,
        bot_username: str,
    ):
        return await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=movie.storage_chat_id,
            message_id=movie.storage_message_id,
            caption=caption or "",
            reply_markup=movie_share_keyboard(bot_username, movie.code),
            protect_content=True,
        )

    async def send_movie_by_code(
        self,
        bot,
        chat_id: int,
        raw_code: str,
        user_id: int | None = None,
    ) -> dict:
        code = (raw_code or "").strip()
        movie = await self.movie_repository.get_by_code(code)

        if not movie:
            return {
                "ok": False,
                "message": "Bunday kino topilmadi. Kod noto'g'ri yoki kino hozircha mavjud emas.",
            }

        bot_info = await bot.get_me()
        cleaned_caption = build_user_movie_caption(movie, bot_info.username)

        try:
            await self.send_protected_movie_to_user(
                bot=bot,
                chat_id=chat_id,
                movie=movie,
                caption=cleaned_caption,
                bot_username=bot_info.username,
            )
        except TelegramForbiddenError:
            return {
                "ok": False,
                "message": "Bot sizga kino yubora olmadi. Iltimos, botni blokdan chiqaring va qayta urinib ko'ring.",
            }
        except TelegramBadRequest:
            return {
                "ok": False,
                "message": "Kinoni yuborib bo'lmadi. Iltimos, keyinroq qayta urinib ko'ring.",
            }
        except TelegramAPIError:
            return {
                "ok": False,
                "message": "Telegram bilan vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            }

        if user_id is not None and hasattr(self.movie_repository, "record_movie_received"):
            try:
                await self.movie_repository.record_movie_received(user_id, movie)
            except SQLAlchemyError:
                logging.getLogger(__name__).exception(
                    "Kino yuborildi, lekin statistikani yozishda database xatosi | user_id=%s movie_id=%s",
                    user_id,
                    movie.id,
                )

        return {"ok": True, "movie": movie}
