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
            logger.debug(f"Выполнение запроса {method} к {url}")
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
            logger.debug(f"Извлечение записей, пропустить: {skip}, лимит: {limit}")
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
            logger.info(f"Создание новой записи: {obj_in}")
            data = await self._make_request("GET")
            records = data.get("record", [])
            new_id = max(item['id'] for item in records) + 1 if records else 1
            new_item = {**obj_in.model_dump(), 'id': new_id}
            records.append(new_item)
            await self._make_request("PUT", records)
            logger.info(f"Запись создана с помощью ID: {new_id}")
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
            logger.info(f"Удаление записи с ID: {id}")
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
    # JsonBin CRUD
    book_jsonbin_crud = JsonBinCRUDBase(
        model=BookModel,
        bin_id=os.getenv("JSONBIN_BIN_ID")
    )

    logger.info("CRUD репозитории инициализированы успешно")
except Exception as e:
    logger.critical(f"Не удалось инициализировать CRUD репозитории: {str(e)}", exc_info=True)
    raise