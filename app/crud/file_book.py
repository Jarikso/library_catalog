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
        logger.info(f"Инциализация FileCRUD для {model.__name__} в {file_path}")

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
            logger.debug(f"Извлечение записей, пропустить: {skip}, лимит: {limit}")
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
            logger.warning(f"Запись с ID {id} не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка удаления записи {id}: {str(e)}", exc_info=True)
            raise

# Инициализация репозиториев
try:
    # File CRUD
    book_file_crud = FileCRUDBase(
        file_path="books.json",
        model=BookModel
    )

    logger.info("CRUD репозитории инициализированы успешно")
except Exception as e:
    logger.critical(f"Не удалось инициализировать CRUD репозитории: {str(e)}", exc_info=True)
    raise