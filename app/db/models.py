from sqlalchemy import BigInteger, Column, ForeignKey, Table, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtModelMixin, TimeStampModelMixin

user_product = Table(
    "user_products",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True),
)


class User(Base, TimeStampModelMixin):
    """Пользователь."""

    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(default=True, server_default=text("'true'"))

    products: Mapped[list["Product"]] = relationship(secondary=user_product, back_populates="users", lazy="joined")

    def __str__(self):
        return f"User {self.telegram_id}"

    def __repr__(self):
        return f"<User(id='{self.id}', telegram_id='{self.telegram_id}')>"


class Product(Base, TimeStampModelMixin):
    """Товар."""

    url: Mapped[str]
    title: Mapped[str] = mapped_column(nullable=True)
    deleted: Mapped[bool] = mapped_column(default=False, server_default=text("'false'"))
    number: Mapped[str]
    sku_id: Mapped[str] = mapped_column(nullable=True)

    users: Mapped[list["User"]] = relationship(secondary=user_product, back_populates="products")
    prices: Mapped[list["ProductPrice"]] = relationship(
        "ProductPrice", back_populates="product", lazy="joined", order_by="-ProductPrice.id"
    )

    __table_args__ = (UniqueConstraint("number", "sku_id", name="unique_product"),)

    def __str__(self):
        title = self.title or self.url
        return f"Product {title[:20]}"

    def __repr__(self):
        return f"<Product(title='{self.title}')>"


class ProductPrice(Base, CreatedAtModelMixin):
    """Цена товара."""

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    price: Mapped[float] = mapped_column(nullable=True)
    product: Mapped["Product"] = relationship("Product", back_populates="prices")

    def __repr__(self):
        return f"<ProductPrice(id='{self.id}')>"
