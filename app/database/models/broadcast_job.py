from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"

    __table_args__ = (
        Index("ix_broadcast_jobs_status", "status"),
        Index("ix_broadcast_jobs_campaign_id", "campaign_id"),
        Index("ix_broadcast_jobs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("broadcast_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_progress_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
