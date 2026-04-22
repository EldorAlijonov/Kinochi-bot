from sqlalchemy import String, Boolean, BigInteger, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        UniqueConstraint("chat_username", name="uq_subscriptions_chat_username"),
        UniqueConstraint("chat_id", name="uq_subscriptions_chat_id"),
        UniqueConstraint("invite_link", name="uq_subscriptions_invite_link"),
        Index("ix_subscriptions_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_type: Mapped[str] = mapped_column(String(50), nullable=False)
    chat_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    invite_link: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
