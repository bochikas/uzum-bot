import contextlib
import logging
from asyncio import current_task
from typing import AsyncGenerator, AsyncIterator, Iterable, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from db.base import Base, DatabaseSessionManagerInitError
from db.models import Product, User

logger = logging.getLogger(__name__)


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
            raise
        finally:
            logger.debug("DB session closed")
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
        async for session in get_session():
            self.db_session = session
            break

    async def close(self):
        if self.db_session:
            await self.db_session.close()

    async def get_user_by_telegram_id(self, telegram_id) -> User:
        result = await self.db_session.execute(select(User).filter_by(telegram_id=telegram_id, active=True))
        return result.scalar()

    async def get_products_by_user_id(self, user_id) -> Iterable[Product]:
        result = (await self.db_session.execute(select(Product).filter_by(user_id=user_id, deleted=False))).unique()
        return result.scalars().all()

    async def create_object(self, model: Type[Base], **kwargs) -> Base:
        obj = model(**kwargs)
        self.db_session.add(obj)
        await self.db_session.commit()
        await self.db_session.refresh(obj)
        return obj

    async def delete_user_product(self, product_id: int) -> None:
        await self.update_object(Product, object_id=product_id, deleted=True)

    async def update_object(self, model: Type[Base], object_id, **kwargs):
        query = await self.db_session.execute(select(model).filter_by(id=object_id))
        obj = query.scalar()

        if not obj:
            return

        changed = False
        for key, value in kwargs.items():
            if hasattr(obj, key) and getattr(obj, key) != value:
                setattr(obj, key, value)
                changed = True

        if changed:
            await self.db_session.commit()
            await self.db_session.refresh(obj)
