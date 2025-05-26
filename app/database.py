import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.session import sessionmaker
from fastapi import HTTPException
from typing import Any

# Настройка логирования
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler: logging.StreamHandler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/mentor_work")

# Инициализация движка БД
engine: AsyncEngine
AsyncSessionLocal: sessionmaker[AsyncSession]

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    logger.info("Database engine created successfully")

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Async session factory configured")

except Exception as e:
    logger.critical(f"Failed to initialize database connection: {str(e)}")
    raise HTTPException(
        status_code=500,
        detail="Database initialization failed"
    )

Base: Any = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий БД.

    Yields:
        AsyncSession: Асинхронная сессия для работы с БД

    Raises:
        HTTPException: В случае ошибок работы с БД
    """
    session: AsyncSession | None = None
    try:
        session = AsyncSessionLocal()
        logger.debug("Сеанс базы данных создан")
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных: {str(e)}")
        if session is not None:
            await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        ) from e
    finally:
        if session is not None:
            await session.close()
            logger.debug("Сеанас базы даннхы закрыт")