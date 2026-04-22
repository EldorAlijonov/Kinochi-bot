import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.db import Base
from app.repositories.pending_movie_request_repository import PendingMovieRequestRepository


class PendingMovieRequestRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_set_and_pop_pending_movie_request(self):
        async with self.session_maker() as session:
            repository = PendingMovieRequestRepository(session)
            await repository.set_pending_request(
                user_telegram_id=777,
                movie_code="0007",
                ttl_seconds=60,
            )

        async with self.session_maker() as session:
            repository = PendingMovieRequestRepository(session)
            movie_code = await repository.pop_valid_movie_code(777)

        self.assertEqual(movie_code, "0007")

        async with self.session_maker() as session:
            repository = PendingMovieRequestRepository(session)
            self.assertIsNone(await repository.pop_valid_movie_code(777))


if __name__ == "__main__":
    unittest.main()
