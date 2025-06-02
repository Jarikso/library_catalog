import aiohttp
import ssl
import certifi
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Self

from app.tools.logger import setup_logger

logger = setup_logger(__name__)

class BaseApiClient(ABC):
    def __init__(self, base_url: str) -> None:
        """
        Инициализация базового API клиента.

        Args:
            base_url: Базовый URL API
        """
        self.base_url = base_url
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.logger = setup_logger(__name__)
        self._session: aiohttp.ClientSession | None = None
        logger.info(f"Инициализация API клиента для {base_url}")

    async def __aenter__(self) -> Self:
        """Создает сессию при входе в контекст"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Закрывает сессию при выходе из контекста"""
        if self._session:
            await self._session.close()
            self._session = None

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

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Конечная точка API
            params: Параметры запроса
            headers: Заголовки запроса
            data: Тело запроса

        Returns:
            Ответ в виде словаря или None в случае ошибки

        Raises:
            RuntimeError: Если метод вызван вне контекстного менеджера
        """
        if self._session is None:
            raise RuntimeError("Сессия не инициализирована. Используйте контекстный менеджер (async with)")

        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug(
                f"Making {method} request to {url} "
                f"with params: {params}, headers: {headers}"
            )
            async with self._session.request(
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