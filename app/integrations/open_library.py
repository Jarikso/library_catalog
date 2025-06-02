import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv

from app.interface.base_api_client import BaseApiClient
from app.tools.logger import setup_logger
from app.schemas.open import OpenLibraryBookInfo

load_dotenv()

logger = setup_logger(__name__)


class OpenLibraryClient(BaseApiClient):
    """Клиент для работы с API Open Library."""

    def __init__(self) -> None:
        """Инициализация клиента Open Library."""
        super().__init__(base_url=os.getenv("OPEN_LIB_BASE"))
        self.cover_url: str = os.getenv("OPEN_LIB_COVER_URL")
        logger.info("Инициализация OpenLibraryClient")

    async def search(self, title: str, author: Optional[str] = None) -> Optional[OpenLibraryBookInfo]:
        """
        Поиск информации о книге в Open Library.

        Args:
            title: Название книги для поиска
            author: Автор книги (опционально)

        Returns:
            Optional[OpenLibraryBookInfo]: Информация о книге или None, если не найдена

        Raises:
            ValueError: Если произошла ошибка при обработке данных
        """
        try:
            logger.info(f"Книга найдена: title='{title}'{f', author={author}' if author else ''}")
            query = f"title:{title}"
            if author:
                query += f" AND author:{author}"

            endpoint = f"/search.json?q={query}"
            data = await self._make_request("GET", endpoint)

            if not data or not data.get("docs"):
                logger.info(f"Нет результата поиска для: {query}")
                return None

            book_data = data["docs"][0]
            logger.debug(f"Книга найдена: {book_data.get('key', 'unknown')}")
            result = OpenLibraryBookInfo()

            # Извлекаем основную информацию
            if 'first_publish_year' in book_data:
                result.first_publish_year = book_data['first_publish_year']
                logger.debug(f"Найден год публикации: {result.first_publish_year}")

            # Получаем обложку если доступна
            if 'cover_i' in book_data:
                result.cover_url = f"{self.cover_url}/id/{book_data['cover_i']}-M.jpg"
                logger.debug(f"Найден URL обложки: {result.cover_url}")

            # Получаем дополнительные детали если доступен work ID
            match book_data:
                case {'first_publish_year': year}:
                    result.first_publish_year = year
                    logger.debug(f"Найден год публикации: {year}")

                case {'cover_i': cover_id}:
                    result.cover_url = f"{self.cover_url}/id/{cover_id}-M.jpg"
                    logger.debug(f"Найден URL обложки: {result.cover_url}")

                case {'key': key}:
                    work_id = key.split('/')[-1]
                    details = await self.get_details(work_id)
                    if details:
                        self._process_details(details, result)

            logger.info(f"Успешно найдена инфлрмация о книги: {title}")
            return result

        except Exception as e:
            logger.error(f"Ошибка поиска книги '{title}': {str(e)}", exc_info=True)
            raise ValueError(f"Failed to search book: {str(e)}") from e

    async def get_details(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию о работе (книге).

        Args:
            work_id: Идентификатор работы в Open Library

        Returns:
            Optional[Dict]: Детальная информация о книге или None, если не найдена

        Raises:
            ValueError: Если произошла ошибка при запросе
        """
        try:
            logger.info(f"Получение данных для работы: {work_id}")
            endpoint = f"/works/{work_id}.json"
            data = await self._make_request("GET", endpoint)

            if not data:
                logger.debug(f"Данные по работе не найдены: {work_id}")
                return None

            logger.debug(f"Успешно получены данные для работы: {work_id}")
            return data

        except Exception as e:
            logger.error(f"Ошибка получения данных по работе {work_id}: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get work details: {str(e)}") from e


    @staticmethod
    def _process_details(details: Dict[str, Any], result: OpenLibraryBookInfo) -> None:

        match details:
            case {'description': str(desc)}:
                result.description = desc
                logger.info("Описание найдено (str)")

            case {'description': {'value': val}}:
                result.description = val
                logger.info("Описание найдено (dict)")

            case {'rating': {'average': rating}} if rating is not None:
                result.rating = rating
                logger.info(f"Найден рейтинг: {rating}")

            case _:
                logger.info("Не найдено дополнительных деталей для обработки")