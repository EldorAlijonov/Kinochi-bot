import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.errors import (
    MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE,
    is_movie_title_schema_mismatch,
)
from app.utils.movie_caption import build_storage_movie_caption
from app.utils.movie_code import (
    MAX_MOVIE_CODE,
    generate_random_movie_code,
    is_movie_code,
)
from app.utils.movie_title import normalize_movie_title

logger = logging.getLogger(__name__)


class MovieCodePoolExhaustedError(RuntimeError):
    pass


class MovieService:
    SUPPORTED_CONTENT_TYPES = {"video", "document", "animation", "audio", "photo"}
    CODE_SAVE_ATTEMPTS = 10

    def __init__(self, movie_repository):
        self.movie_repository = movie_repository

    @staticmethod
    def normalize_code(raw_code: str) -> str:
        return (raw_code or "").strip()

    async def generate_unique_code(self) -> str:
        if await self.movie_repository.count_all() >= MAX_MOVIE_CODE:
            raise MovieCodePoolExhaustedError(
                "Barcha kodlar band (9999 ta kino to'lgan)"
            )

        while True:
            code = generate_random_movie_code()
            if not await self.movie_repository.exists_by_code(code):
                return code

    @staticmethod
    def _database_error_message(error: SQLAlchemyError) -> str:
        if is_movie_title_schema_mismatch(error):
            return MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE

        return "Database bilan ishlashda xatolik yuz berdi. Iltimos, loglarni tekshiring."

    @classmethod
    def extract_media_metadata(cls, message):
        content_type = message.content_type
        if content_type not in cls.SUPPORTED_CONTENT_TYPES:
            return None

        file_unique_id = None
        file_size = None
        if message.video:
            file_unique_id = message.video.file_unique_id
            file_size = message.video.file_size
        elif message.document:
            file_unique_id = message.document.file_unique_id
            file_size = message.document.file_size
        elif message.animation:
            file_unique_id = message.animation.file_unique_id
            file_size = message.animation.file_size
        elif message.audio:
            file_unique_id = message.audio.file_unique_id
            file_size = message.audio.file_size
        elif message.photo:
            file_unique_id = message.photo[-1].file_unique_id
            file_size = message.photo[-1].file_size

        return {
            "content_type": content_type,
            "file_unique_id": file_unique_id,
            "file_size": file_size,
            "caption": message.caption,
        }

    async def upload_movie_to_base(
        self,
        bot,
        movie_base,
        source_message,
    ):
        media_metadata = self.extract_media_metadata(source_message)
        if not media_metadata:
            return {
                "ok": False,
                "message": "Faqat video, document, animation, audio yoki photo yuborish mumkin.",
            }

        movie_title = normalize_movie_title(media_metadata["caption"])
        bot_username = await self._get_bot_username(bot)

        try:
            stored_message = await bot.copy_message(
                chat_id=movie_base.chat_id,
                from_chat_id=source_message.chat.id,
                message_id=source_message.message_id,
            )
        except TelegramBadRequest:
            return {
                "ok": False,
                "message": "Kinoni bazaga yuborib bo'lmadi. Bot kanalga yozish huquqini tekshiring.",
            }

        for attempt in range(1, self.CODE_SAVE_ATTEMPTS + 1):
            try:
                code = await self.generate_unique_code()
                storage_caption = build_storage_movie_caption(
                    media_metadata["caption"],
                    movie_title,
                    code,
                    file_size=media_metadata["file_size"],
                    channel_username=movie_base.chat_username,
                    bot_username=bot_username,
                )
                await bot.edit_message_caption(
                    chat_id=movie_base.chat_id,
                    message_id=stored_message.message_id,
                    caption=storage_caption,
                )
                movie = await self.movie_repository.create_movie(
                    movie_base_id=movie_base.id,
                    code=code,
                    title=movie_title,
                    content_type=media_metadata["content_type"],
                    storage_chat_id=movie_base.chat_id,
                    storage_message_id=stored_message.message_id,
                    file_unique_id=media_metadata["file_unique_id"],
                    caption=storage_caption,
                    original_chat_id=source_message.chat.id,
                    original_message_id=source_message.message_id,
                )
                return {"ok": True, "movie": movie}
            except MovieCodePoolExhaustedError as error:
                await self._cleanup_copied_movie(bot, movie_base.chat_id, stored_message.message_id)
                return {"ok": False, "message": str(error)}
            except IntegrityError:
                logger.warning("Kino kodi collision bo'ldi, retry qilinmoqda | attempt=%s", attempt)
                continue
            except TelegramBadRequest:
                await self._cleanup_copied_movie(bot, movie_base.chat_id, stored_message.message_id)
                return {
                    "ok": False,
                    "message": "Kinoning captionini yangilab bo'lmadi. Bot kanalga yozish huquqini tekshiring.",
                }
            except SQLAlchemyError as error:
                logger.exception("Kinoni databasega saqlashda xatolik")
                await self._cleanup_copied_movie(bot, movie_base.chat_id, stored_message.message_id)
                return {
                    "ok": False,
                    "message": self._database_error_message(error),
                }

        await self._cleanup_copied_movie(bot, movie_base.chat_id, stored_message.message_id)
        return {
            "ok": False,
            "message": "Kino kodi uchun 10 marta urinish amalga oshirildi, lekin saqlab bo'lmadi.",
        }

    @staticmethod
    async def _cleanup_copied_movie(bot, chat_id: int, message_id: int) -> None:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError:
            logger.exception(
                "Saqlanmagan kino postini o'chirishda Telegram xatosi | chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )

    @staticmethod
    async def _get_bot_username(bot) -> str | None:
        if not hasattr(bot, "get_me"):
            return None

        bot_info = await bot.get_me()
        return getattr(bot_info, "username", None)

    async def process_channel_movie_post(self, bot, movie_base, channel_post):
        media_metadata = self.extract_media_metadata(channel_post)
        if not media_metadata:
            return None

        movie_title = normalize_movie_title(media_metadata["caption"])
        bot_username = await self._get_bot_username(bot)
        for attempt in range(1, self.CODE_SAVE_ATTEMPTS + 1):
            try:
                code = await self.generate_unique_code()
                storage_caption = build_storage_movie_caption(
                    media_metadata["caption"],
                    movie_title,
                    code,
                    file_size=media_metadata["file_size"],
                    channel_username=movie_base.chat_username,
                    bot_username=bot_username,
                )
                await bot.edit_message_caption(
                    chat_id=channel_post.chat.id,
                    message_id=channel_post.message_id,
                    caption=storage_caption,
                )
                return await self.movie_repository.create_movie(
                    movie_base_id=movie_base.id,
                    code=code,
                    title=movie_title,
                    content_type=media_metadata["content_type"],
                    storage_chat_id=channel_post.chat.id,
                    storage_message_id=channel_post.message_id,
                    file_unique_id=media_metadata["file_unique_id"],
                    caption=storage_caption,
                    original_chat_id=channel_post.chat.id,
                    original_message_id=channel_post.message_id,
                )
            except MovieCodePoolExhaustedError:
                logger.warning("Kino kodi pool tugagan")
                return None
            except IntegrityError:
                logger.warning("Kanal postida kino kodi collision bo'ldi | attempt=%s", attempt)
                continue
            except TelegramBadRequest:
                return None
            except SQLAlchemyError:
                logger.exception("Kanal postidan kinoni databasega saqlashda xatolik")
                return None

        return None

    async def get_movie_by_code(self, raw_code: str):
        code = self.normalize_code(raw_code)
        if not is_movie_code(code):
            return None
        return await self.movie_repository.get_by_code(code)
