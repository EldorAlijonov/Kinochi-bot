from datetime import datetime

from sqlalchemy import func, select, update

from app.database.models.broadcast import BroadcastCampaign, BroadcastDelivery
from app.database.models.broadcast_job import BroadcastJob


class BroadcastRepository:
    def __init__(self, session):
        self.session = session

    async def create_campaign(
        self,
        admin_id: int,
        content_type: str,
        text: str | None,
        file_id: str | None,
        source_chat_id: int,
        source_message_id: int,
        target_type: str,
        status: str = "created",
    ) -> BroadcastCampaign:
        campaign = BroadcastCampaign(
            admin_id=admin_id,
            content_type=content_type,
            text=text,
            file_id=file_id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            target_type=target_type,
            status=status,
        )
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def create_job(
        self,
        campaign_id: int,
        admin_chat_id: int | None = None,
    ) -> BroadcastJob:
        job = BroadcastJob(
            campaign_id=campaign_id,
            status="queued",
            admin_chat_id=admin_chat_id,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def claim_next_job(self) -> tuple[BroadcastJob, BroadcastCampaign] | None:
        result = await self.session.execute(
            select(BroadcastJob, BroadcastCampaign)
            .join(BroadcastCampaign, BroadcastCampaign.id == BroadcastJob.campaign_id)
            .where(BroadcastJob.status == "queued")
            .order_by(BroadcastJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        row = result.first()
        if not row:
            return None

        job, campaign = row
        job.status = "sending"
        job.started_at = datetime.now()
        campaign.status = "sending"
        await self.session.commit()
        await self.session.refresh(job)
        await self.session.refresh(campaign)
        return job, campaign

    async def update_job_progress(
        self,
        job_id: int,
        *,
        processed_count: int,
        sent_count: int,
        failed_count: int,
    ) -> bool:
        result = await self.session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(
                processed_count=processed_count,
                sent_count=sent_count,
                failed_count=failed_count,
            )
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def finish_job(
        self,
        job_id: int,
        campaign_id: int,
        status: str,
        error_text: str | None = None,
    ) -> None:
        await self.session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(
                status=status,
                error_text=error_text,
                finished_at=datetime.now(),
            )
        )
        await self.session.execute(
            update(BroadcastCampaign)
            .where(BroadcastCampaign.id == campaign_id)
            .values(status=status)
        )
        await self.session.commit()

    async def retry_or_fail_job(
        self,
        job_id: int,
        campaign_id: int,
        *,
        error_text: str,
        max_retries: int,
    ) -> str:
        result = await self.session.execute(
            select(BroadcastJob.retry_count).where(BroadcastJob.id == job_id)
        )
        retry_count = result.scalar_one_or_none()
        next_retry_count = (retry_count or 0) + 1
        error_text = error_text[:1000]

        if next_retry_count < max_retries:
            status = "queued"
            finished_at = None
        else:
            status = "failed"
            finished_at = datetime.now()

        await self.session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(
                status=status,
                retry_count=next_retry_count,
                error_text=error_text,
                finished_at=finished_at,
            )
        )
        await self.session.execute(
            update(BroadcastCampaign)
            .where(BroadcastCampaign.id == campaign_id)
            .values(status=status)
        )
        await self.session.commit()
        return status

    async def request_cancel_job(self, job_id: int) -> bool:
        result = await self.session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id, BroadcastJob.status.in_(("queued", "sending")))
            .values(cancel_requested=True)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def is_job_cancel_requested(self, job_id: int) -> bool:
        result = await self.session.execute(
            select(BroadcastJob.cancel_requested).where(BroadcastJob.id == job_id)
        )
        return bool(result.scalar_one_or_none())

    async def create_delivery(
        self,
        campaign_id: int,
        target_type: str,
        target_chat_id: int | None,
        target_identifier: str | None,
        sent_message_id: int | None,
        delivery_status: str,
        error_text: str | None = None,
    ) -> BroadcastDelivery:
        delivery = BroadcastDelivery(
            campaign_id=campaign_id,
            target_type=target_type,
            target_chat_id=target_chat_id,
            target_identifier=target_identifier,
            sent_message_id=sent_message_id,
            delivery_status=delivery_status,
            error_text=error_text,
        )
        self.session.add(delivery)
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    def add_delivery(
        self,
        campaign_id: int,
        target_type: str,
        target_chat_id: int | None,
        target_identifier: str | None,
        sent_message_id: int | None,
        delivery_status: str,
        error_text: str | None = None,
    ) -> BroadcastDelivery:
        delivery = BroadcastDelivery(
            campaign_id=campaign_id,
            target_type=target_type,
            target_chat_id=target_chat_id,
            target_identifier=target_identifier,
            sent_message_id=sent_message_id,
            delivery_status=delivery_status,
            error_text=error_text,
        )
        self.session.add(delivery)
        return delivery

    async def flush_deliveries(self) -> None:
        await self.session.commit()

    async def list_campaigns(self, limit: int = 10, offset: int = 0) -> list[BroadcastCampaign]:
        result = await self.session.execute(
            select(BroadcastCampaign)
            .order_by(BroadcastCampaign.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_campaigns(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(BroadcastCampaign)
        )
        return result.scalar_one()

    async def get_campaign_by_id(self, campaign_id: int) -> BroadcastCampaign | None:
        result = await self.session.execute(
            select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_deliveries_by_campaign(self, campaign_id: int) -> list[BroadcastDelivery]:
        result = await self.session.execute(
            select(BroadcastDelivery)
            .where(BroadcastDelivery.campaign_id == campaign_id)
            .order_by(BroadcastDelivery.id.asc())
        )
        return list(result.scalars().all())

    async def list_deliveries_by_campaign_after(
        self,
        campaign_id: int,
        last_delivery_id: int,
        limit: int,
    ) -> list[BroadcastDelivery]:
        result = await self.session.execute(
            select(BroadcastDelivery)
            .where(
                BroadcastDelivery.campaign_id == campaign_id,
                BroadcastDelivery.id > last_delivery_id,
            )
            .order_by(BroadcastDelivery.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_campaign_status(self, campaign_id: int, status: str) -> bool:
        result = await self.session.execute(
            update(BroadcastCampaign)
            .where(BroadcastCampaign.id == campaign_id)
            .values(status=status)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def mark_campaign_deleted(self, campaign_id: int, status: str = "deleted") -> bool:
        result = await self.session.execute(
            update(BroadcastCampaign)
            .where(BroadcastCampaign.id == campaign_id)
            .values(is_deleted=(status == "deleted"), status=status)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def mark_delivery_deleted(self, delivery_id: int) -> bool:
        result = await self.session.execute(
            update(BroadcastDelivery)
            .where(BroadcastDelivery.id == delivery_id)
            .values(delivery_status="deleted", deleted_at=datetime.now())
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def count_deliveries_by_status(self, campaign_id: int) -> dict[str, int]:
        result = await self.session.execute(
            select(BroadcastDelivery.delivery_status, func.count())
            .where(BroadcastDelivery.campaign_id == campaign_id)
            .group_by(BroadcastDelivery.delivery_status)
        )
        return {status: count for status, count in result.all()}
