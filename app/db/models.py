from sqlalchemy import BigInteger, ForeignKey, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Пользователь."""

    telegram_id: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(default=True, server_default=text("'true'"))

    products: Mapped[list["Product"]] = relationship("Product", back_populates="user", lazy="joined")

    def __str__(self):
        return f"User {self.telegram_id}"

    def __repr__(self):
        return f"<User(id='{self.id}', telegram_id='{self.telegram_id}')>"


class Product(Base):
    """Товар."""

    url: Mapped[str]
    title: Mapped[str] = mapped_column(nullable=True)
    price: Mapped[float] = mapped_column(nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    deleted: Mapped[bool] = mapped_column(default=False, server_default=text("'false'"))
    number: Mapped[str]
    sku_id: Mapped[str] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="products")

    __table_args__ = (UniqueConstraint("number", "sku_id", name="unique_product"),)

    def __str__(self):
        title = self.title = self.url
        return f"Product {title[:20]}"

    def __repr__(self):
        return f"<Product(title='{self.title}', price='{self.price}')>"
