import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.db import Base
from app.database.models.movie import Movie
from app.database.models.movie_base import MovieBase
from app.repositories.movie_base_repository import MovieBaseRepository
from app.repositories.movie_repository import MovieRepository


class MovieRepositoryIntegrationTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_create_movie_base_and_movie(self):
        async with self.session_maker() as session:
            base_repository = MovieBaseRepository(session)
            movie_base = await base_repository.create_base(
                title="Test baza",
                base_type="public_channel",
                chat_id=-1001234567890,
                chat_username="@testbase",
                invite_link="https://t.me/testbase",
            )

        async with self.session_maker() as session:
            movie_repository = MovieRepository(session)
            movie = await movie_repository.create_movie(
                movie_base_id=movie_base.id,
                code="0001",
                content_type="video",
                storage_chat_id=-1001234567890,
                storage_message_id=15,
                file_unique_id="file-1",
            )

        async with self.session_maker() as session:
            movie_repository = MovieRepository(session)
            fetched = await movie_repository.get_by_code("0001")

        self.assertIsNotNone(fetched)
        self.assertEqual(movie.id, fetched.id)
        self.assertEqual(fetched.storage_message_id, 15)

    async def test_get_by_code_ignores_inactive_movie_base(self):
        async with self.session_maker() as session:
            base_repository = MovieBaseRepository(session)
            movie_base = await base_repository.create_base(
                title="Noaktiv baza",
                base_type="public_channel",
                chat_id=-1001234567000,
                chat_username="@inactivebase",
                invite_link="https://t.me/inactivebase",
            )
            await base_repository.deactivate_base(movie_base.id)

        async with self.session_maker() as session:
            movie_repository = MovieRepository(session)
            await movie_repository.create_movie(
                movie_base_id=movie_base.id,
                code="0002",
                content_type="video",
                storage_chat_id=-1001234567000,
                storage_message_id=20,
                file_unique_id="file-2",
            )

        async with self.session_maker() as session:
            movie_repository = MovieRepository(session)
            fetched = await movie_repository.get_by_code("0002")

        self.assertIsNone(fetched)


if __name__ == "__main__":
    unittest.main()
