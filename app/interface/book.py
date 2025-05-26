import logging
from fastapi import APIRouter
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Type, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Аннотации типов
ModelType = TypeVar('ModelType')  # Тип SQLAlchemy модели
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)
ExternalBookInfoType = TypeVar('ExternalBookInfoType', bound=BaseModel)
ResponseSchemaType = TypeVar('ResponseSchemaType', bound=BaseModel)


class BaseBookRouter(ABC):
    """Абстрактный базовый класс для всех книжных роутеров"""

    def __init__(self) -> None:
        """Инициализация роутера с настройкой маршрутов"""
        self.router: APIRouter = APIRouter()
        logger.info(f"Инициализация {self.__class__.__name__}")
        self._setup_routes()
        logger.debug("Настройка маршрутов завершина")

    @abstractmethod
    def _setup_routes(self) -> None:
        """Настройка маршрутов API"""
        logger.debug("Setting up routes")
        pass

    @abstractmethod
    async def create_book(self, book: CreateSchemaType) -> ResponseSchemaType:
        """
        Создать книгу

        Args:
            book: Данные для создания книги

        Returns:
            ResponseSchemaType: Созданная книга

        Raises:
            HTTPException: В случае ошибки создания
        """
        logger.info(f"Creating book: {book}")
        pass

    @abstractmethod
    async def read_books(self, skip: int = 0, limit: int = 100) -> List[ResponseSchemaType]:
        """
        Получить список книг

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[ResponseSchemaType]: Список книг

        Raises:
            HTTPException: В случае ошибки чтения
        """
        logger.debug(f"Чтение книги, начало={skip}, лимит={limit}")
        pass

    @abstractmethod
    async def read_book(self, book_id: int) -> ResponseSchemaType:
        """
        Получить книгу по ID

        Args:
            book_id: Идентификатор книги

        Returns:
            ResponseSchemaType: Найденная книга

        Raises:
            HTTPException: Если книга не найдена или произошла ошибка
        """
        logger.info(f"Reading book with ID: {book_id}")
        pass

    @abstractmethod
    async def update_book(self, book_id: int, book: UpdateSchemaType) -> ResponseSchemaType:
        """
        Обновить книгу

        Args:
            book_id: Идентификатор книги
            book: Данные для обновления

        Returns:
            ResponseSchemaType: Обновленная книга

        Raises:
            HTTPException: Если книга не найдена или произошла ошибка
        """
        logger.info(f"Обновление данных о книги: {book_id}, данные: {book}")
        pass

    @abstractmethod
    async def delete_book(self, book_id: int) -> ResponseSchemaType:
        """
        Удалить книгу

        Args:
            book_id: Идентификатор книги

        Returns:
            ResponseSchemaType: Удаленная книга

        Raises:
            HTTPException: Если книга не найдена или произошла ошибка
        """
        logger.info(f"Удаление данных о книги: {book_id}")
        pass


class BaseBookRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """Абстрактный базовый класс для репозитория книг"""

    def __init__(self) -> None:
        logger.info(f"Initializing {self.__class__.__name__}")

    # 1. CRUD операции
    @abstractmethod
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """
        Получить книгу по ID

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги

        Returns:
            Optional[ModelType]: Найденная книга или None

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        logger.debug(f"Получение книги по ID: {id}")
        pass

    @abstractmethod
    async def get_multi(
            self,
            db: AsyncSession,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """
        Получить список книг с пагинацией

        Args:
            db: Асинхронная сессия БД
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей

        Returns:
            List[ModelType]: Список книг

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        logger.debug(f"Получение множества книг, начало={skip}, максимально={limit}")
        pass

    @abstractmethod
    async def create(
            self,
            db: AsyncSession,
            obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Создать новую книгу

        Args:
            db: Асинхронная сессия БД
            obj_in: Данные для создания книги

        Returns:
            ModelType: Созданная книга

        Raises:
            SQLAlchemyError: В случае ошибки БД
            ValueError: В случае невалидных данных
        """
        logger.info(f"Создание новой книги: {obj_in}")
        pass

    @abstractmethod
    async def update(
            self,
            db: AsyncSession,
            id: int,
            obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        Обновить существующую книгу

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги
            obj_in: Данные для обновления

        Returns:
            Optional[ModelType]: Обновленная книга или None, если не найдена

        Raises:
            SQLAlchemyError: В случае ошибки БД
            ValueError: В случае невалидных данных
        """
        logger.info(f"Обновление данных по ID: {id}, данные: {obj_in}")
        pass

    @abstractmethod
    async def delete(
            self,
            db: AsyncSession,
            id: int
    ) -> Optional[ModelType]:
        """
        Удалить книгу

        Args:
            db: Асинхронная сессия БД
            id: Идентификатор книги

        Returns:
            Optional[ModelType]: Удаленная книга или None, если не найдена

        Raises:
            SQLAlchemyError: В случае ошибки БД
        """
        logger.info(f"Удаление книги по ID: {id}")
        pass

    # 2. Работа с внешними API
    @abstractmethod
    async def fetch_external_book_info(
            self,
            title: str,
            author: Optional[str] = None
    ) -> Optional[ExternalBookInfoType]:
        """
        Получить информацию о книге из внешнего API

        Args:
            title: Название книги
            author: Автор книги (опционально)

        Returns:
            Optional[ExternalBookInfoType]: Информация о книге или None

        Raises:
            HTTPException: В случае ошибки API
            ValueError: В случае невалидных данных
        """
        logger.info(f"Получение дополнительной информации о {title}{f' {author}' if author else ''}")
        pass

    # 3. Комбинированные методы
    @abstractmethod
    async def create_with_external_data(
            self,
            db: AsyncSession,
            obj_in: CreateSchemaType,
            fetch_external: bool = True
    ) -> ModelType:
        """
        Создать книгу с возможностью дополнения данными из внешних источников

        Args:
            db: Асинхронная сессия БД
            obj_in: Данные для создания книги
            fetch_external: Флаг получения дополнительных данных из API

        Returns:
            ModelType: Созданная книга

        Raises:
            SQLAlchemyError: В случае ошибки БД
            HTTPException: В случае ошибки API
            ValueError: В случае невалидных данных
        """
        logger.info(f"Создание книги с дополнительными данными {obj_in}")
        pass