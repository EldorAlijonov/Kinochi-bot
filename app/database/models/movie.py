from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class Movie(Base):
    __tablename__ = "movies"

    __table_args__ = (
        UniqueConstraint("code", name="uq_movies_code"),
        Index("ix_movies_code", "code"),
        Index("ix_movies_movie_base_id", "movie_base_id"),
        Index("ix_movies_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_base_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movie_bases.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(4), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Nomsiz kino")
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    file_unique_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    original_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    original_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
