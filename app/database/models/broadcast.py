from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"

    __table_args__ = (
        Index("ix_broadcast_campaigns_created_at", "created_at"),
        Index("ix_broadcast_campaigns_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BroadcastDelivery(Base):
    __tablename__ = "broadcast_deliveries"

    __table_args__ = (
        Index("ix_broadcast_deliveries_campaign_id", "campaign_id"),
        Index("ix_broadcast_deliveries_target_type", "target_type"),
        Index("ix_broadcast_deliveries_delivery_status", "delivery_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("broadcast_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
