from urllib.parse import parse_qs, urlparse

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.db import async_session_maker
from app.repositories.movie_repository import MovieRepository
from app.services.movie_service import MovieService
from app.utils.movie_code import is_movie_code
from app.utils.share_text import build_general_share_text, build_movie_share_text

router = Router()
logger = logging.getLogger(__name__)


def _extract_movie_code(query: str | None) -> str | None:
    value = (query or "").strip()
    if value.startswith("share_"):
        value = value.removeprefix("share_")

    parsed_url = urlparse(value)
    if parsed_url.scheme in {"http", "https"} and parsed_url.netloc.lower() == "t.me":
        start_payload = parse_qs(parsed_url.query).get("start", [None])[0]
        if start_payload:
            value = start_payload.strip()

    if is_movie_code(value):
        return value

    return None


@router.inline_query()
async def share_movie_inline_query(inline_query: InlineQuery):
    movie_code = _extract_movie_code(inline_query.query)
    if not movie_code:
        try:
            bot_info = await inline_query.bot.get_me()
        except TelegramAPIError:
            logger.exception("Inline share bot ma'lumotini olishda Telegram xatosi")
            await inline_query.answer(
                results=[],
                cache_time=1,
                is_personal=True,
            )
            return

        referral_code = f"ref_{inline_query.from_user.id}"
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="general_share",
                    title="🎬 Kinolar botini ulashish",
                    description="Do'stingizga bot havolasini yuboring",
                    input_message_content=InputTextMessageContent(
                        message_text=build_general_share_text(
                            bot_info.username,
                            referral_code,
                        ),
                    ),
                )
            ],
            cache_time=1,
            is_personal=True,
        )
        return

    try:
        async with async_session_maker() as session:
            movie_repository = MovieRepository(session)
            movie_service = MovieService(movie_repository)
            movie = await movie_service.get_movie_by_code(movie_code)
    except SQLAlchemyError:
        logger.exception("Inline share kinoni olishda database xatosi | code=%s", movie_code)
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return

    if not movie:
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return

    try:
        bot_info = await inline_query.bot.get_me()
    except TelegramAPIError:
        logger.exception("Inline share bot ma'lumotini olishda Telegram xatosi")
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return
    movie_title = " ".join((movie.title or "").strip().split()) or "Kino"
    share_text = build_movie_share_text(bot_info.username, movie_title, movie.code)

    await inline_query.answer(
        results=[
            InlineQueryResultArticle(
                id=f"movie_share_{movie.code}",
                title=f"🎬 {movie_title}",
                description="Kino havolasini do'stingizga yuboring",
                input_message_content=InputTextMessageContent(
                    message_text=share_text,
                ),
            )
        ],
        cache_time=1,
        is_personal=True,
    )
