import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.db import Base
from app.repositories.subscription_repository import SubscriptionRepository


class SubscriptionRepositoryIntegrationTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_create_and_fetch_public_channel(self):
        async with self.session_maker() as session:
            repository = SubscriptionRepository(session)
            created = await repository.create_public_channel(
                title="Test kanal",
                chat_username="@testchannel",
                invite_link="https://t.me/testchannel",
            )

        async with self.session_maker() as session:
            repository = SubscriptionRepository(session)
            fetched = await repository.get_by_username("@testchannel")

        self.assertIsNotNone(fetched)
        self.assertEqual(created.id, fetched.id)
        self.assertEqual(fetched.title, "Test kanal")

    async def test_exists_by_invite_link_detects_saved_link(self):
        async with self.session_maker() as session:
            repository = SubscriptionRepository(session)
            await repository.create_external_link(
                title="Docs",
                invite_link="https://example.com/docs",
            )

        async with self.session_maker() as session:
            repository = SubscriptionRepository(session)
            exists = await repository.exists_by_invite_link("https://example.com/docs")

        self.assertTrue(exists)


if __name__ == "__main__":
    unittest.main()
