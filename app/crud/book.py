from typing import Type, TypeVar, Generic, Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
import json
import os
import aiohttp
from dotenv import load_dotenv
import ssl
import certifi

from app.schemas.book import Book, BookCreate, BookUpdate
from app.integrations.open_library import OpenLibraryClient
from app.interface.book import BaseBookRepository
from app.models.book import Book as BookModel
from app.tools.logger import setup_logger

# Настройка логирования
logger = setup_logger(__name__)

load_dotenv()

ModelType = TypeVar('ModelType', bound=Any)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class BookRepository(BaseBookRepository[BookModel, BookCreate, BookUpdate]):
    """Репозиторий для работы с книгами в базе данных."""

    def __init__(self, model: Type[BookModel], api_client: OpenLibraryClient) -> None:
        """
        Инициализация репозитория.

        Args:
            model: SQLAlchemy модель книги
            api_client: Клиент для работы с OpenLibrary API
        """
        self.model: Type[BookModel] = model
        self.api_client: OpenLibraryClient = api_client
        logger.info(f"Инициализация BookRepository для модели: {model.__name__}")

    async def get(self, db: AsyncSession, id: int) -> Optional[BookModel]:
        """
        Получить книгу по ID.

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги

        Returns:
            Optional[BookModel]: Найденная книга или None

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        try:
            logger.debug(f"Извлечение книги с ID: {id}")
            result = await db.execute(select(self.model).filter(self.model.id == id))
            book = result.scalars().first()
            if not book:
                logger.debug(f"Книга не найдена с ID: {id}")
            return book
        except SQLAlchemyError as e:
            logger.error(f"Ошибка извлечения книги {id}: {str(e)}", exc_info=True)
            raise

    async def get_multi(
            self,
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[BookModel]:
        """
        Получить список книг с пагинацией.

        Args:
            db: Асинхронная сессия БД
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[BookModel]: Список книг

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        try:
            logger.debug(f"Извлечение книги, начиная: {skip}, ограничение: {limit}")
            result = await db.execute(select(self.model).offset(skip).limit(limit))
            books = result.scalars().all()
            logger.debug(f"Найденный {len(books)} книг")
            return books
        except SQLAlchemyError as e:
            logger.error(f"Ошибка извлечения книги: {str(e)}", exc_info=True)
            raise

    async def create(
            self,
            db: AsyncSession,
            *,
            obj_in: BookCreate
    ) -> BookModel:
        """
        Создать новую книгу.

        Args:
            db: Асинхронная сессия БД
            obj_in: Данные для создания книги

        Returns:
            BookModel: Созданная книга

        Raises:
            SQLAlchemyError: В случае ошибки БД
            ValueError: В случае невалидных данных
        """
        try:
            logger.info(f"Создана новая книга: {obj_in.title}")

            # Получаем дополнительную информацию из Open Library
            open_lib_info = await self.api_client.search(obj_in.title, obj_in.author)
            logger.debug(f"OpenLibrary репозиторий: {open_lib_info}")

            # Объединяем данные
            create_data = obj_in.model_dump()
            if open_lib_info:
                if open_lib_info.cover_url:
                    create_data['cover_url'] = open_lib_info.cover_url
                if open_lib_info.description:
                    create_data['description'] = open_lib_info.description
                if open_lib_info.rating is not None:
                    create_data['rating'] = open_lib_info.rating
                if open_lib_info.first_publish_year and 'year' not in create_data:
                    create_data['year'] = open_lib_info.first_publish_year

            # Создаем книгу
            db_obj = self.model(**create_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Создана книга с ID: {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Ошибка создания книги: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Непредвиденная ошибка создания книги: {str(e)}", exc_info=True)
            raise

    async def update(
            self,
            db: AsyncSession,
            *,
            id: int,
            obj_in: BookUpdate
    ) -> Optional[BookModel]:
        """
        Обновить существующую книгу.

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги
            obj_in: Данные для обновления

        Returns:
            Optional[BookModel]: Обновленная книга или None, если не найдена

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        try:
            logger.info(f"Обновление книги с ID: {id}")
            result = await db.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**obj_in.model_dump(exclude_unset=True))
                .returning(self.model)
            )
            await db.commit()
            book = result.scalars().first()
            if book:
                logger.info(f"Данные книги с ID {id} обновлены")
            else:
                logger.warning(f"Данные книги с ID {id} не обновлены")
            return book
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Ошибка обновления книги {id}: {str(e)}", exc_info=True)
            raise

    async def delete(
            self,
            db: AsyncSession,
            *,
            id: int
    ) -> Optional[BookModel]:
        """
        Удалить книгу.

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги

        Returns:
            Optional[BookModel]: Удаленная книга или None, если не найдена

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        try:
            logger.info(f"Удаление книги с идентификатором: {id}")
            result = await db.execute(
                delete(self.model)
                .where(self.model.id == id)
                .returning(self.model)
            )
            await db.commit()
            book = result.scalars().first()
            if book:
                logger.info(f"Книга с ID: {id} удалена")
            else:
                logger.warning(f"Книга с ID {id} не найдена для удаления")
            return book
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Ошибка удаления книги {id}: {str(e)}", exc_info=True)
            raise

    async def fetch_external_book_info(
            self,
            title: str,
            author: Optional[str] = None
    ) -> Optional[Any]:
        """
        Получить информацию о книге из внешнего API.

        Args:
            title: Название книги
            author: Автор книги (опционально)

        Returns:
            Optional[Any]: Информация о книге или None

        Raises:
            Exception: В случае ошибки API
        """
        try:
            logger.info(f"Извлечение внешней информации для книги: {title}")
            return await self.api_client.search(title, author)
        except Exception as e:
            logger.error(f"Ошибка получения внешней информации: {str(e)}", exc_info=True)
            raise

    async def create_with_external_data(
            self,
            db: AsyncSession,
            obj_in: BookCreate,
            fetch_external: bool = True
    ) -> BookModel:
        """
        Создать книгу с возможностью дополнения данными из внешних источников.

        Args:
            db: Асинхронная сессия БД
            obj_in: Данные для создания книги
            fetch_external: Флаг получения дополнительных данных из API

        Returns:
            BookModel: Созданная книга

        Raises:
            SQLAlchemyError: В случае ошибки БД
            Exception: В случае ошибки API
        """
        try:
            logger.info(f"Создание книги с внешними данными: {obj_in.title}")
            create_data = obj_in.model_dump()

            if fetch_external:
                external_info = await self.fetch_external_book_info(obj_in.title, obj_in.author)
                if external_info:
                    if external_info.cover_url:
                        create_data['cover_url'] = external_info.cover_url
                    if external_info.description:
                        create_data['description'] = external_info.description

            db_obj = self.model(**create_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Книга создана с использованеи внешних данных, ID: {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Ошибка создания книги с внешними данными: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Ошибка получения внешних данных: {str(e)}", exc_info=True)
            raise


# Инициализация репозиториев
try:
    # Database CRUD
    book_db_crud = BookRepository(
        model=BookModel,
        api_client=OpenLibraryClient()
    )

    logger.info("CRUD репозитории инициализированы успешно")
except Exception as e:
    logger.critical(f"Не удалось инициализировать CRUD репозитории: {str(e)}", exc_info=True)
    raise