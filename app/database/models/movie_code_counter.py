from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class MovieCodeCounter(Base):
    __tablename__ = "movie_code_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
