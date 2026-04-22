from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.database.models.movie import Movie
from app.database.models.movie_base import MovieBase
from app.database.models.user_action_log import UserActionLog


class MovieBaseRepository:
    def __init__(self, session):
        self.session = session

    async def create_base(
        self,
        title: str,
        base_type: str,
        chat_id: int,
        chat_username: str | None = None,
        invite_link: str | None = None,
    ) -> MovieBase:
        movie_base = MovieBase(
            title=title,
            base_type=base_type,
            chat_id=chat_id,
            chat_username=chat_username,
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(movie_base)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(movie_base)
        return movie_base

    async def get_by_id(self, movie_base_id: int) -> MovieBase | None:
        result = await self.session.execute(
            select(MovieBase).where(MovieBase.id == movie_base_id)
        )
        return result.scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> MovieBase | None:
        result = await self.session.execute(
            select(MovieBase).where(MovieBase.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, chat_username: str) -> MovieBase | None:
        result = await self.session.execute(
            select(MovieBase).where(MovieBase.chat_username == chat_username)
        )
        return result.scalar_one_or_none()

    async def exists_by_chat_id(self, chat_id: int) -> bool:
        return await self.get_by_chat_id(chat_id) is not None

    async def exists_by_username(self, chat_username: str) -> bool:
        return await self.get_by_username(chat_username) is not None

    async def get_all_paginated(self, limit: int, offset: int) -> list[MovieBase]:
        result = await self.session.execute(
            select(MovieBase)
            .order_by(MovieBase.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_active_bases(self) -> list[MovieBase]:
        result = await self.session.execute(
            select(MovieBase)
            .where(MovieBase.is_active.is_(True))
            .order_by(MovieBase.id.desc())
        )
        return result.scalars().all()

    async def list_inactive_bases(self) -> list[MovieBase]:
        result = await self.session.execute(
            select(MovieBase)
            .where(MovieBase.is_active.is_(False))
            .order_by(MovieBase.id.desc())
        )
        return result.scalars().all()

    async def get_paginated_by_active(
        self,
        is_active: bool,
        limit: int,
        offset: int,
    ) -> list[MovieBase]:
        result = await self.session.execute(
            select(MovieBase)
            .where(MovieBase.is_active.is_(is_active))
            .order_by(MovieBase.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(MovieBase)
        )
        return result.scalar_one()

    async def count_bases(self) -> int:
        return await self.count_all()

    async def count_active_bases(self) -> int:
        return await self.count_by_active(True)

    async def count_by_active(self, is_active: bool) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MovieBase)
            .where(MovieBase.is_active.is_(is_active))
        )
        return result.scalar_one()

    async def activate_base(self, base_id: int) -> bool:
        return await self._set_active(base_id, True)

    async def deactivate_base(self, base_id: int) -> bool:
        return await self._set_active(base_id, False)

    async def get_base_by_id(self, base_id: int) -> MovieBase | None:
        return await self.get_by_id(base_id)

    async def _set_active(self, base_id: int, is_active: bool) -> bool:
        movie_base = await self.get_by_id(base_id)
        if not movie_base:
            return False

        movie_base.is_active = is_active
        await self.session.commit()
        return True

    async def delete_by_id(self, movie_base_id: int) -> bool:
        movie_base = await self.get_by_id(movie_base_id)
        if not movie_base:
            return False

        await self.session.execute(
            delete(Movie).where(Movie.movie_base_id == movie_base_id)
        )
        await self.session.delete(movie_base)
        await self.session.commit()
        return True

    async def get_base_usage_stats(self, limit: int = 10) -> list[tuple[MovieBase, int, int]]:
        movie_count = func.count(func.distinct(Movie.id)).label("movie_count")
        usage_count = func.count(UserActionLog.id).label("usage_count")
        result = await self.session.execute(
            select(MovieBase, movie_count, usage_count)
            .outerjoin(Movie, Movie.movie_base_id == MovieBase.id)
            .outerjoin(
                UserActionLog,
                (UserActionLog.movie_id == Movie.id)
                & (UserActionLog.action_type == "movie_received"),
            )
            .group_by(MovieBase.id)
            .order_by(usage_count.desc(), movie_count.desc(), MovieBase.id.desc())
            .limit(limit)
        )
        return list(result.all())
