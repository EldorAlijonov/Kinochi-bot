from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_joined_at", "joined_at"),
        Index("ix_users_last_active_at", "last_active_at"),
        Index("ix_users_referred_by", "referred_by"),
    )

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    start_payload: Mapped[str | None] = mapped_column(String(255), nullable=True)
