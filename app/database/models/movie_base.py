from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class MovieBase(Base):
    __tablename__ = "movie_bases"

    __table_args__ = (
        UniqueConstraint("chat_username", name="uq_movie_bases_chat_username"),
        UniqueConstraint("chat_id", name="uq_movie_bases_chat_id"),
        Index("ix_movie_bases_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    base_type: Mapped[str] = mapped_column(String(50), nullable=False)
    chat_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invite_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
