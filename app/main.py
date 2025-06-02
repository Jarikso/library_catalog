from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import engine, Base
from app.tools.logger import setup_logger
from app.routes.books import db_router
from app.routes.file_book import file_router
from app.routes.jsonbin_book import jsonbin_router


logger = setup_logger(__name__)

app = FastAPI(title="Book Library API")
router = APIRouter()

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Обработчик HTTP исключений.

    Args:
        request: Запрос, вызвавший исключение
        exc: Исключение HTTPException

    Returns:
        JSONResponse: Ответ с деталями ошибки
    """
    logger.error(f"HTTPException: {exc.detail} (status_code={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Обработчик ошибок валидации запросов.

    Args:
        request: Запрос с невалидными данными
        exc: Исключение RequestValidationError

    Returns:
        JSONResponse: Ответ с деталями ошибок валидации
    """
    logger.error(f"Ошибка валидации: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"message": "Validation error", "errors": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    Обработчик всех неожиданных исключений.

    Args:
        request: Запрос, вызвавший исключение
        exc: Перехваченное исключение

    Returns:
        JSONResponse: Ответ с сообщением об ошибке
    """
    logger.error(f"Неожиданная ошибка: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

# Создание таблиц
async def create_tables():
    """
    Создает таблицы в базе данных.

    Args:
        engine: Асинхронный движок SQLAlchemy
        base: Базовый класс моделей SQLAlchemy

    Raises:
        HTTPException: Если не удалось создать таблицы
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы базы данных созданы уcпешно")
    except Exception as e:
        logger.error(f"Ошибка создания таблиц базы данных: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Неудалось инициализировать таблицы базы данных"
        )

@app.on_event("startup")
async def startup_event():
    """
    Обработчик события запуска приложения.
    Создает таблицы в базе данных при старте.
    """
    try:
        await create_tables()
    except Exception as e:
        logger.critical(f"Ошибка запуска приложения: {str(e)}")
        raise

app.include_router(db_router.router, prefix="/db", tags=["database_books"])
app.include_router(file_router.router, prefix="/file", tags=["file_books"])
appрр.include_router(jsonbin_router.router, prefix="/jsonbin", tags=["jsonbin_books"])