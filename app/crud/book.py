import logging
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

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)

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
            logger.debug(f"Found {len(books)} books")
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
            logger.info(f"Creating new book: {obj_in.title}")

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
            logger.info(f"Updating book with ID: {id}")
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
            logger.info(f"Deleting book with ID: {id}")
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
            logger.info(f"Creating book with external data: {obj_in.title}")
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


class FileCRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый CRUD для работы с данными в файле."""

    def __init__(self, file_path: str, model: Type[ModelType]) -> None:
        """
        Инициализация файлового CRUD.

        Args:
            file_path: Путь к файлу с данными
            model: Pydantic модель данных
        """
        self.file_path: str = file_path
        self.model: Type[ModelType] = model
        self._ensure_file_exists()
        logger.info(f"Initialized FileCRUD for {model.__name__} at {file_path}")

    def _ensure_file_exists(self) -> None:
        """Создает файл, если он не существует."""
        try:
            if not os.path.exists(self.file_path):
                with open(self.file_path, 'w') as f:
                    json.dump([], f)
                logger.debug(f"Создан новый файл в {self.file_path}")
        except IOError as e:
            logger.error(f"Ошибка создания файла {self.file_path}: {str(e)}", exc_info=True)
            raise

    def _read_data(self) -> List[Dict[str, Any]]:
        """Читает данные из файла."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка чтения файла {self.file_path}: {str(e)}", exc_info=True)
            raise

    def _write_data(self, data: List[Dict[str, Any]]) -> None:
        """Записывает данные в файл."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Ошибка записи в файл {self.file_path}: {str(e)}", exc_info=True)
            raise

    async def get(self, id: int) -> Optional[ModelType]:
        """
        Получить запись по ID.

        Args:
            id: Идентификатор записи

        Returns:
            Optional[ModelType]: Найденная запись или None
        """
        try:
            logger.debug(f"Извлечение записи с ID: {id}")
            data = self._read_data()
            item = next((item for item in data if item['id'] == id), None)
            if not item:
                logger.debug(f"Запись с ID: {id} не найдена")
            return self.model(**item) if item else None
        except Exception as e:
            logger.error(f"Ошибка получения файла {id}: {str(e)}", exc_info=True)
            raise

    async def get_multi(
            self,
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """
        Получить список записей с пагинацией.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[ModelType]: Список записей
        """
        try:
            logger.debug(f"Fetching records, skip: {skip}, limit: {limit}")
            data = self._read_data()
            return [self.model(**item) for item in data[skip:skip + limit]]
        except Exception as e:
            logger.error(f"Ошибка извлечения файла: {str(e)}", exc_info=True)
            raise

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создать новую запись.

        Args:
            obj_in: Данные для создания записи

        Returns:
            ModelType: Созданная запись
        """
        try:
            logger.info(f"Создание новой щаписи: {obj_in}")
            data = self._read_data()
            new_id = max(item['id'] for item in data) + 1 if data else 1
            new_item = {**obj_in.model_dump(), 'id': new_id}
            data.append(new_item)
            self._write_data(data)
            logger.info(f"Запись создана с ID: {new_id}")
            return self.model(**new_item)
        except Exception as e:
            logger.error(f"Ошибка записи: {str(e)}", exc_info=True)
            raise

    async def update(
            self,
            *,
            id: int,
            obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        Обновить существующую запись.

        Args:
            id: Идентификатор записи
            obj_in: Данные для обновления

        Returns:
            Optional[ModelType]: Обновленная запись или None, если не найдена
        """
        try:
            logger.info(f"Обновление записи с ID: {id}")
            data = self._read_data()
            for idx, item in enumerate(data):
                if item['id'] == id:
                    updated_item = {**item, **obj_in.model_dump(exclude_unset=True)}
                    data[idx] = updated_item
                    self._write_data(data)
                    logger.info(f"Запись с ID {id} обновлена")
                    return self.model(**updated_item)
            logger.warning(f"Запись с ID {id} для обновления не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка обновления записи {id}: {str(e)}", exc_info=True)
            raise

    async def delete(self, *, id: int) -> Optional[ModelType]:
        """
        Удалить запись.

        Args:
            id: Идентификатор записи

        Returns:
            Optional[ModelType]: Удаленная запись или None, если не найдена
        """
        try:
            logger.info(f"Удаление записи с ID: {id}")
            data = self._read_data()
            for idx, item in enumerate(data):
                if item['id'] == id:
                    deleted_item = data.pop(idx)
                    self._write_data(data)
                    logger.info(f"Запись с  ID {id} удалена")
                    return self.model(**deleted_item)
            logger.warning(f"ЗАпись с ID {id} не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка удаления записи {id}: {str(e)}", exc_info=True)
            raise


class JsonBinCRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый CRUD для работы с JsonBin.io."""

    def __init__(
            self,
            model: Type[ModelType],
            bin_id: Optional[str] = None
    ) -> None:
        """
        Инициализация JsonBin CRUD.

        Args:
            model: Pydantic модель данных
            bin_id: Идентификатор бина (опционально)
        """
        self.model: Type[ModelType] = model
        self.api_key: Optional[str] = os.getenv("JSONBIN_API_KEY")
        self.bin_id: str = os.getenv("JSONBIN_BIN_ID") if bin_id is None else bin_id
        self.base_url: str = f"https://api.jsonbin.io/v3/b/{self.bin_id}"
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "X-Master-Key": self.api_key,
        }
        self.ssl_context: ssl.SSLContext = ssl.create_default_context(
            cafile=certifi.where()
        )
        logger.info(f"Инициализация JsonBinCRUD для {model.__name__}")

    async def _make_request(
            self,
            method: str,
            data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Выполнить запрос к JsonBin API.

        Args:
            method: HTTP метод
            data: Тело запроса

        Returns:
            Dict[str, Any]: Ответ API

        Raises:
            aiohttp.ClientError: В случае ошибки сети
            ValueError: В случае невалидного ответа
        """
        url = f"{self.base_url}"
        try:
            logger.debug(f"Making {method} request to {url}")
            async with aiohttp.ClientSession() as session:
                async with session.request(
                        method,
                        url,
                        headers=self.headers,
                        json=data,
                        ssl=self.ssl_context
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"Запрос к {url} выполнен успешно.")
                    return result
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети {method} {url}: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка{method} {url}: {str(e)}", exc_info=True)
            raise

    async def get(self, id: int) -> Optional[ModelType]:
        """
        Получить запись по ID.

        Args:
            id: Идентификатор записи

        Returns:
            Optional[ModelType]: Найденная запись или None
        """
        try:
            logger.debug(f"Извлечение записи с ID: {id}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            item = next((item for item in records if item['id'] == id), None)
            if not item:
                logger.debug(f"Запись с ID {id} не найдена")
            return self.model(**item) if item else None
        except Exception as e:
            logger.error(f"Ошибка получения записи {id}: {str(e)}", exc_info=True)
            raise

    async def get_multi(
            self,
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """
        Получить список записей с пагинацией.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[ModelType]: Список записей
        """
        try:
            logger.debug(f"Fetching records, skip: {skip}, limit: {limit}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            return [self.model(**item) for item in records[skip:skip + limit]]
        except Exception as e:
            logger.error(f"Ошибка извлечения записи: {str(e)}", exc_info=True)
            raise

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создать новую запись.

        Args:
            obj_in: Данные для создания записи

        Returns:
            ModelType: Созданная запись
        """
        try:
            logger.info(f"Creating new record: {obj_in}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            new_id = max(item['id'] for item in records) + 1 if records else 1
            new_item = {**obj_in.model_dump(), 'id': new_id}
            records.append(new_item)
            await self._make_request("PUT", records)
            logger.info(f"Record created with ID: {new_id}")
            return self.model(**new_item)
        except Exception as e:
            logger.error(f"Ошибка создания записи: {str(e)}", exc_info=True)
            raise

    async def update(
            self,
            *,
            id: int,
            obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        Обновить существующую запись.

        Args:
            id: Идентификатор записи
            obj_in: Данные для обновления

        Returns:
            Optional[ModelType]: Обновленная запись или None, если не найдена
        """
        try:
            logger.info(f"Обновление записи с ID: {id}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            for idx, item in enumerate(records):
                if item['id'] == id:
                    updated_item = {**item, **obj_in.model_dump(exclude_unset=True)}
                    records[idx] = updated_item
                    await self._make_request("PUT", records)
                    logger.info(f"Запись обновления с ID: {id}")
                    return self.model(**updated_item)
            logger.warning(f"Запись не найдена для записи, ID: {id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка обновления записи {id}: {str(e)}", exc_info=True)
            raise

    async def delete(self, *, id: int) -> Optional[ModelType]:
        """
        Удалить запись.

        Args:
            id: Идентификатор записи

        Returns:
            Optional[ModelType]: Удаленная запись или None, если не найдена
        """
        try:
            logger.info(f"Deleting record with ID: {id}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            for idx, item in enumerate(records):
                if item['id'] == id:
                    deleted_item = records.pop(idx)
                    await self._make_request("PUT", records)
                    logger.info(f"Запись с ID удалена: {id}")
                    return self.model(**deleted_item)
            logger.warning(f"Запись для удаления не найдена, ID: {id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка удаления записи {id}: {str(e)}", exc_info=True)
            raise


# Инициализация репозиториев
try:
    # Database CRUD
    book_db_crud = BookRepository(
        model=BookModel,
        api_client=OpenLibraryClient()
    )

    # File CRUD
    book_file_crud = FileCRUDBase(
        file_path="books.json",
        model=BookModel
    )

    # JsonBin CRUD
    book_jsonbin_crud = JsonBinCRUDBase(
        model=BookModel,
        bin_id=os.getenv("JSONBIN_BIN_ID")
    )

    logger.info("CRUD репозитории инициализированы успешно")
except Exception as e:
    logger.critical(f"Не удалось инициализировать CRUD репозитории: {str(e)}", exc_info=True)
    raise