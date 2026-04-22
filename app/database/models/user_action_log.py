from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class UserActionLog(Base):
    __tablename__ = "user_action_logs"

    __table_args__ = (
        Index("ix_user_action_logs_action_created", "action_type", "created_at"),
        Index("ix_user_action_logs_user_created", "user_telegram_id", "created_at"),
        Index("ix_user_action_logs_movie_id", "movie_id"),
        Index("ix_user_action_logs_subscription_id", "subscription_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    movie_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    movie_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    payload: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
