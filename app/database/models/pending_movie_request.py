from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class PendingMovieRequest(Base):
    __tablename__ = "pending_movie_requests"

    __table_args__ = (
        Index("ix_pending_movie_requests_expires_at", "expires_at"),
    )

    user_telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    movie_code: Mapped[str] = mapped_column(String(4), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
