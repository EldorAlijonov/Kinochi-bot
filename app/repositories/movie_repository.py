from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only

from app.database.models.movie import Movie
from app.database.models.movie_base import MovieBase
from app.database.models.user_action_log import UserActionLog


def _today_start() -> datetime:
    current = datetime.now()
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


class MovieRepository:
    def __init__(self, session):
        self.session = session

    async def create_movie(
        self,
        movie_base_id: int,
        code: str,
        content_type: str,
        storage_chat_id: int,
        storage_message_id: int,
        file_unique_id: str | None = None,
        caption: str | None = None,
        title: str = "Nomsiz kino",
        original_chat_id: int | None = None,
        original_message_id: int | None = None,
    ) -> Movie:
        movie = Movie(
            movie_base_id=movie_base_id,
            code=code,
            title=title,
            content_type=content_type,
            storage_chat_id=storage_chat_id,
            storage_message_id=storage_message_id,
            file_unique_id=file_unique_id,
            caption=caption,
            original_chat_id=original_chat_id,
            original_message_id=original_message_id,
            is_active=True,
        )

        self.session.add(movie)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(movie)
        return movie

    async def get_by_code(self, code: str) -> Movie | None:
        result = await self.session.execute(
            select(Movie)
            .join(MovieBase, Movie.movie_base_id == MovieBase.id)
            .where(
                Movie.code == code,
                Movie.is_active.is_(True),
                MovieBase.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code_with_base(self, code: str) -> tuple[Movie, MovieBase] | None:
        result = await self.session.execute(
            select(Movie, MovieBase)
            .join(MovieBase, Movie.movie_base_id == MovieBase.id)
            .where(
                Movie.code == code,
                Movie.is_active.is_(True),
                MovieBase.is_active.is_(True),
            )
        )
        return result.one_or_none()

    async def exists_by_code(self, code: str) -> bool:
        result = await self.session.execute(
            select(Movie.id).where(Movie.code == code).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_storage_message(
        self,
        storage_chat_id: int,
        storage_message_id: int,
    ) -> Movie | None:
        result = await self.session.execute(
            select(Movie).options(load_only(Movie.id)).where(
                Movie.storage_chat_id == storage_chat_id,
                Movie.storage_message_id == storage_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Movie)
        )
        return result.scalar_one()

    async def count_movies(self) -> int:
        return await self.count_all()

    async def count_movies_uploaded_today(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Movie)
            .where(Movie.created_at >= _today_start())
        )
        return result.scalar_one()

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Movie)
            .join(MovieBase, Movie.movie_base_id == MovieBase.id)
            .where(Movie.is_active.is_(True), MovieBase.is_active.is_(True))
        )
        return result.scalar_one()

    async def list_movies(self, limit: int, offset: int) -> list[tuple[Movie, MovieBase]]:
        result = await self.session.execute(
            select(Movie, MovieBase)
            .join(MovieBase, Movie.movie_base_id == MovieBase.id)
            .where(Movie.is_active.is_(True), MovieBase.is_active.is_(True))
            .order_by(Movie.created_at.desc(), Movie.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.all())

    async def list_movies_by_base(
        self,
        movie_base_id: int,
        limit: int,
        offset: int,
    ) -> list[Movie]:
        result = await self.session.execute(
            select(Movie)
            .where(
                Movie.movie_base_id == movie_base_id,
                Movie.is_active.is_(True),
            )
            .order_by(Movie.created_at.desc(), Movie.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def delete_movie(self, code: str) -> bool:
        result = await self.session.execute(
            delete(Movie).where(Movie.code == code)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def get_last_movie(self) -> Movie | None:
        result = await self.session.execute(
            select(Movie)
            .options(load_only(Movie.id, Movie.code))
            .order_by(Movie.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_last_movie_code(self) -> str | None:
        result = await self.session.execute(
            select(Movie.code).order_by(Movie.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def record_movie_received(self, user_telegram_id: int, movie: Movie):
        action = UserActionLog(
            user_telegram_id=user_telegram_id,
            action_type="movie_received",
            movie_id=movie.id,
            movie_code=movie.code,
        )
        self.session.add(action)
        await self.session.commit()
        return action

    async def get_top_movies(self, limit: int = 5) -> list[tuple[Movie, int]]:
        result = await self.session.execute(
            select(Movie, func.count(UserActionLog.id).label("total"))
            .join(UserActionLog, UserActionLog.movie_id == Movie.id)
            .where(UserActionLog.action_type == "movie_received")
            .group_by(Movie.id)
            .order_by(func.count(UserActionLog.id).desc(), Movie.id.desc())
            .limit(limit)
        )
        return list(result.all())

    async def get_most_used_codes(self, limit: int = 5) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(UserActionLog.movie_code, func.count(UserActionLog.id).label("total"))
            .where(
                UserActionLog.action_type.in_(("code_sent", "share_start", "movie_received")),
                UserActionLog.movie_code.is_not(None),
            )
            .group_by(UserActionLog.movie_code)
            .order_by(func.count(UserActionLog.id).desc())
            .limit(limit)
        )
        return [(row.movie_code, row.total) for row in result.all()]

    async def get_most_active_base(self) -> tuple[MovieBase, int] | None:
        result = await self.session.execute(
            select(MovieBase, func.count(UserActionLog.id).label("total"))
            .join(Movie, Movie.movie_base_id == MovieBase.id)
            .join(UserActionLog, UserActionLog.movie_id == Movie.id)
            .where(UserActionLog.action_type == "movie_received")
            .group_by(MovieBase.id)
            .order_by(func.count(UserActionLog.id).desc(), MovieBase.id.desc())
            .limit(1)
        )
        return result.one_or_none()
