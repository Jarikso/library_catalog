from uuid import UUID
from datetime import datetime
from typing import ClassVar, Any, Optional
from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text
from ..database import Base


class Book(Base):
    __tablename__ = "books"
    mapper_args: ClassVar[dict[Any, Any]] = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    author: Mapped[str]
    year: Mapped[int]
    genre: Mapped[str]
    pages: Mapped[int]
    available: Mapped[bool] = mapped_column(default=True)

    cover_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)