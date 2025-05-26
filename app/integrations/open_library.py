import logging

from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.interface.base_api_client import BaseApiClient

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class OpenLibraryBookInfo(BaseModel):
    cover_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    first_publish_year: Optional[int] = None


class OpenLibraryClient(BaseApiClient):
    """Клиент для работы с API Open Library."""

    def __init__(self) -> None:
        """Инициализация клиента Open Library."""
        super().__init__(base_url="https://openlibrary.org")
        self.cover_url: str = "https://covers.openlibrary.org/b"
        logger.info("OpenLibraryClient initialized")

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
            if 'key' in book_data:
                work_id = book_data['key'].split('/')[-1]
                details = await self.get_details(work_id)
                if details:
                    if 'description' in details:
                        if isinstance(details['description'], str):
                            result.description = details['description']
                        elif 'value' in details['description']:
                            result.description = details['description']['value']
                        logger.debug("Ошисание найдено")

                    if 'rating' in details:
                        result.rating = details.get('rating', {}).get('average', None)
                        logger.debug(f"Найден рейтинг: {result.rating}")

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
            logger.debug(f"Получение данных для работы: {work_id}")
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