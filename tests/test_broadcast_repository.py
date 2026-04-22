import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.db import Base
from app.repositories.broadcast_repository import BroadcastRepository


class BroadcastRepositoryTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_retry_or_fail_job_requeues_until_max_retries(self):
        async with self.session_maker() as session:
            repository = BroadcastRepository(session)
            campaign = await repository.create_campaign(
                admin_id=1,
                content_type="text",
                text="Reklama",
                file_id=None,
                source_chat_id=10,
                source_message_id=20,
                target_type="users",
                status="queued",
            )
            job = await repository.create_job(campaign_id=campaign.id, admin_chat_id=1)

            status = await repository.retry_or_fail_job(
                job.id,
                campaign.id,
                error_text="temporary",
                max_retries=3,
            )

            self.assertEqual(status, "queued")

            status = await repository.retry_or_fail_job(
                job.id,
                campaign.id,
                error_text="temporary again",
                max_retries=3,
            )

            self.assertEqual(status, "queued")

            status = await repository.retry_or_fail_job(
                job.id,
                campaign.id,
                error_text="final error",
                max_retries=3,
            )

            self.assertEqual(status, "failed")


if __name__ == "__main__":
    unittest.main()
