import aiohttp
import ssl
import certifi
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)

class BaseApiClient(ABC):
    def __init__(self, base_url: str) -> None:
        """
        Инициализация базового API клиента.

        Args:
            base_url: Базовый URL API
        """
        self.base_url = base_url
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.logger = logging.getLogger(__name__)
        logger.info(f"Инициализация API клиента для {base_url}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict]:
        """
        Базовый метод для выполнения HTTP-запросов
        :param method: HTTP метод (GET, POST, PUT, DELETE)
        :param endpoint: Конечная точка API
        :param params: Параметры запроса
        :param headers: Заголовки запроса
        :param data: Тело запроса
        :return: Ответ в виде словаря или None в случае ошибки
        """
        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug(
                f"Making {method} request to {url} "
                f"with params: {params}, headers: {headers}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=data,
                    ssl=self.ssl_context
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            self.logger.error(f"Ошибка при выполнении запроса {method} {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при выполнении запроса {method} {url}: {str(e)}")
            return None

    @abstractmethod
    async def search(self, *args, **kwargs) -> Any:
        """
        Абстрактный метод для поиска данных в API.

        Returns:
            Результаты поиска в формате, специфичном для реализации

        Raises:
            NotImplementedError: Если метод не реализован
            aiohttp.ClientError: В случае ошибок сети
        """
        pass

    @abstractmethod
    async def get_details(self, *args, **kwargs) -> Any:
        """
        Абстрактный метод для получения детальной информации.

        Returns:
            Детальная информация в формате, специфичном для реализации

        Raises:
            NotImplementedError: Если метод не реализован
            aiohttp.ClientError: В случае ошибок сети
        """
        pass