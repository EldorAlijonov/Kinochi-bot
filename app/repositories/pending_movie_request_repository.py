from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.models.pending_movie_request import PendingMovieRequest


def _now() -> datetime:
    return datetime.now(UTC)


def _is_expired(expires_at: datetime) -> bool:
    now = (
        datetime.now(expires_at.tzinfo)
        if expires_at.tzinfo
        else datetime.now(UTC).replace(tzinfo=None)
    )
    return expires_at <= now


class PendingMovieRequestRepository:
    def __init__(self, session):
        self.session = session

    async def set_pending_request(
        self,
        user_telegram_id: int,
        movie_code: str,
        ttl_seconds: int,
    ) -> PendingMovieRequest:
        expires_at = _now() + timedelta(seconds=ttl_seconds)
        dialect = self.session.bind.dialect.name if self.session.bind else ""

        if dialect == "postgresql":
            statement = (
                pg_insert(PendingMovieRequest)
                .values(
                    user_telegram_id=user_telegram_id,
                    movie_code=movie_code,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    index_elements=[PendingMovieRequest.user_telegram_id],
                    set_={
                        "movie_code": movie_code,
                        "expires_at": expires_at,
                    },
                )
                .returning(PendingMovieRequest)
            )
            result = await self.session.execute(statement)
            await self.session.commit()
            return result.scalar_one()

        existing = await self.get_raw_request(user_telegram_id)
        if existing:
            existing.movie_code = movie_code
            existing.expires_at = expires_at
            await self.session.commit()
            return existing

        request = PendingMovieRequest(
            user_telegram_id=user_telegram_id,
            movie_code=movie_code,
            expires_at=expires_at,
        )
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get_raw_request(
        self,
        user_telegram_id: int,
    ) -> PendingMovieRequest | None:
        result = await self.session.execute(
            select(PendingMovieRequest).where(
                PendingMovieRequest.user_telegram_id == user_telegram_id
            )
        )
        return result.scalar_one_or_none()

    async def pop_valid_movie_code(self, user_telegram_id: int) -> str | None:
        request = await self.get_raw_request(user_telegram_id)
        if not request:
            return None

        await self.session.delete(request)
        await self.session.commit()

        if _is_expired(request.expires_at):
            return None

        return request.movie_code

    async def delete_request(self, user_telegram_id: int) -> bool:
        result = await self.session.execute(
            delete(PendingMovieRequest).where(
                PendingMovieRequest.user_telegram_id == user_telegram_id
            )
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def delete_expired(self) -> int:
        result = await self.session.execute(
            delete(PendingMovieRequest).where(
                PendingMovieRequest.expires_at <= _now()
            )
        )
        await self.session.commit()
        return int(result.rowcount or 0)
