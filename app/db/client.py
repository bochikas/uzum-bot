import contextlib
import logging
from asyncio import current_task
from typing import AsyncGenerator, AsyncIterator, Iterable, Type, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from db.base import Base, DatabaseSessionManagerInitError
from db.models import Product, ProductPrice, User, user_product

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=Base)


class DatabaseSessionManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    def init(self, host: str):
        self._engine = create_async_engine(host, future=True, poolclass=None)
        self._session_maker = async_sessionmaker(
            bind=self._engine, autocommit=False, expire_on_commit=False, autoflush=False
        )

    async def close(self):
        if self._engine is None:
            raise DatabaseSessionManagerInitError("DatabaseSessionManager not initialized")
        await self._engine.dispose()
        self._engine = None
        self._session_maker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise DatabaseSessionManagerInitError("DatabaseSessionManager not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_maker is None:
            raise DatabaseSessionManagerInitError("DatabaseSessionManager not initialized")

        session = async_scoped_session(self._session_maker, scopefunc=current_task)

        try:
            yield session()
        except Exception:
            await session.rollback()
            logger.exception("Unexpected error in database session")
            raise
        finally:
            logger.debug("Database session closed")
            await session.close()


sessionmanager = DatabaseSessionManager()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with sessionmanager.session() as session:
        yield session


class DBClient:
    db_session: AsyncSession | None = None

    async def __aenter__(self):
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create(self):
        self.db_session = await anext(get_session())

    async def close(self):
        await self.db_session.close()

    async def get_user_by_telegram_id(self, telegram_id) -> User:
        result = await self.db_session.execute(select(User).filter_by(telegram_id=telegram_id, active=True))
        return result.scalar()

    async def get_user_products(self, user_id: int) -> Iterable[Product]:
        """Список товара пользователя."""

        query = select(Product).join(user_product, Product.id == user_product.c.product_id).filter_by(user_id=user_id)
        result = (await self.db_session.execute(query)).unique()
        return result.scalars().all()

    async def delete_user_product(self, user_id: int, product_id: int) -> None:
        query = delete(user_product).where(user_product.c.user_id == user_id, user_product.c.product_id == product_id)
        await self.db_session.execute(query)
        await self.db_session.commit()

    async def add_new_price(self, product_id: int, price: float) -> None:
        self.db_session.add(ProductPrice(product_id=product_id, price=price))
        await self.db_session.commit()

    async def create_and_add_product_to_user(self, user_id: int, url: str, number: str, sku_id: str | None) -> None:
        result = await self.db_session.execute(select(Product).filter_by(number=number, sku_id=sku_id))
        if not (product := result.scalar()):
            product = Product(url=url, number=number, sku_id=sku_id)

        user = await self.get_model_object_by_id(User, user_id)
        user.products.append(product)
        self.db_session.add(user)

        await self.db_session.commit()

    async def get_model_object_by_id(self, model: Type[T], obj_id: int) -> Type[T]:
        result = await self.db_session.execute(select(model).filter_by(id=obj_id))
        return result.scalar()

    async def get_model_objects(self, model: Type[T], **kwargs) -> Iterable[T]:
        result = (await self.db_session.execute(select(model).filter_by(**kwargs))).unique()
        return result.scalars().all()

    async def create_object(self, model: Type[Base], **kwargs) -> Base:
        obj = model(**kwargs)
        self.db_session.add(obj)
        await self.db_session.commit()
        await self.db_session.refresh(obj)
        return obj

    async def update_object(self, model: Type[Base], object_id, **kwargs):
        query = await self.db_session.execute(select(model).filter_by(id=object_id))
        obj = query.scalar()

        if not obj:
            return

        changed = False
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
                changed = True

        if changed:
            await self.db_session.commit()
            await self.db_session.refresh(obj)
