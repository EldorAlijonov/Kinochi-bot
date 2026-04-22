import asyncio
import logging

from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.repositories.broadcast_repository import BroadcastRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.broadcast_service import BroadcastService

logger = logging.getLogger(__name__)


class BroadcastWorker:
    POLL_INTERVAL_SECONDS = 3
    SCHEMA_ERROR_SLEEP_SECONDS = 60
    MAX_JOB_RETRIES = 3

    def __init__(self, bot):
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self.run(), name="broadcast-worker")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def run(self) -> None:
        logger.info("Broadcast worker ishga tushdi")
        while not self._stopped.is_set():
            try:
                processed = await self._process_one_job()
                if not processed:
                    await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            except SQLAlchemyError as error:
                logger.exception(
                    "Broadcast worker database schema xatosi yoki SQL xatosi sabab to'xtab turibdi. "
                    "Alembic migrationlarni tekshiring: alembic upgrade head. error=%s",
                    error,
                )
                await asyncio.sleep(self.SCHEMA_ERROR_SLEEP_SECONDS)
            except Exception:
                logger.exception("Broadcast worker kutilmagan xatolik bilan davom etmoqda")
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

    async def _process_one_job(self) -> bool:
        async with async_session_maker() as session:
            repository = BroadcastRepository(session)
            claimed = await repository.claim_next_job()

        if not claimed:
            return False

        job, campaign = claimed
        logger.info("Broadcast job boshlandi | job_id=%s campaign_id=%s", job.id, campaign.id)

        try:
            async with async_session_maker() as session:
                repository = BroadcastRepository(session)
                service = BroadcastService(
                    user_repository=UserRepository(session),
                    broadcast_repository=repository,
                    subscription_repository=SubscriptionRepository(session),
                )

                async def progress_callback(processed: int, stats: dict) -> None:
                    await repository.update_job_progress(
                        job.id,
                        processed_count=processed,
                        sent_count=stats["users"] + stats["groups"] + stats["channels"],
                        failed_count=stats["failed"],
                    )
                    if job.admin_chat_id:
                        try:
                            await self.bot.send_message(
                                job.admin_chat_id,
                                "Reklama yuborilmoqda...\n"
                                f"Ko'rib chiqildi: <b>{processed}</b>\n"
                                f"Userlar: <b>{stats['users']}</b>\n"
                                f"Guruhlar: <b>{stats['groups']}</b>\n"
                                f"Kanallar: <b>{stats['channels']}</b>\n"
                                f"Xatolik: <b>{stats['failed']}</b>",
                            )
                        except TelegramAPIError:
                            logger.warning(
                                "Broadcast progress xabarini yuborib bo'lmadi | job_id=%s admin_chat_id=%s",
                                job.id,
                                job.admin_chat_id,
                            )

                async def cancel_checker() -> bool:
                    return await repository.is_job_cancel_requested(job.id)

                result = await service.send_campaign(
                    self.bot,
                    campaign,
                    progress_callback=progress_callback,
                    cancel_checker=cancel_checker,
                )
                status = "cancelled" if result.get("cancelled") else (
                    "sent" if result["failed"] == 0 else "partial"
                )
                sent_count = result["users"] + result["groups"] + result["channels"]
                await repository.update_job_progress(
                    job.id,
                    processed_count=sent_count + result["failed"],
                    sent_count=sent_count,
                    failed_count=result["failed"],
                )
                await repository.finish_job(job.id, campaign.id, status)

            if job.admin_chat_id:
                try:
                    await self.bot.send_message(
                        job.admin_chat_id,
                        "Reklama job yakunlandi.\n\n"
                        f"Status: <b>{status}</b>\n"
                        f"Yuborildi: <b>{sent_count}</b>\n"
                        f"Userlar: <b>{result['users']}</b>\n"
                        f"Guruhlar: <b>{result['groups']}</b>\n"
                        f"Kanallar: <b>{result['channels']}</b>\n"
                        f"Kanal xatolari: <b>{result.get('failed_channels', 0)}</b>\n"
                        f"Jami xatolik: <b>{result['failed']}</b>",
                    )
                except TelegramAPIError:
                    logger.warning(
                        "Broadcast yakuniy xabarini yuborib bo'lmadi | job_id=%s admin_chat_id=%s",
                        job.id,
                        job.admin_chat_id,
                    )
        except SQLAlchemyError as error:
            logger.exception("Broadcast job database xatosi | job_id=%s", job.id)
            async with async_session_maker() as session:
                await BroadcastRepository(session).finish_job(
                    job.id,
                    campaign.id,
                    "failed",
                    error_text=str(error)[:1000],
                )
        except Exception as error:
            logger.exception("Broadcast job xatolik sabab to'xtadi | job_id=%s", job.id)
            async with async_session_maker() as session:
                retry_status = await BroadcastRepository(session).retry_or_fail_job(
                    job.id,
                    campaign.id,
                    error_text=str(error),
                    max_retries=self.MAX_JOB_RETRIES,
                )
            logger.warning(
                "Broadcast job retry holati yangilandi | job_id=%s status=%s",
                job.id,
                retry_status,
            )
        return True
