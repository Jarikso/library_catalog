import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.session import sessionmaker
from fastapi import HTTPException
from typing import Any

from app.tools.logger import setup_logger

# Настройка логирования
logger = setup_logger(__name__)

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
    logger.info("database.py - База данных успешно создано")

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Асинхронный сеанс настроен")

except Exception as e:
    logger.critical(f"Не удалось инициализировать соединение с базой данных: {str(e)}")
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