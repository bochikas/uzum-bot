from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa N805
        return f"{cls.__name__.lower()}s"


class CreatedAtModelMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UpdatedAtModelMixin:
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class TimeStampModelMixin(CreatedAtModelMixin, UpdatedAtModelMixin):
    """Миксин."""


class DatabaseSessionManagerInitError(Exception):
    """Ошибка менеджера сессий бд"""
