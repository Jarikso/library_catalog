from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from pydantic import BaseModel

from app.schemas import book as schema
from app.crud.book import book_db_crud
from app.database import get_db
from app.interface.book import BaseBookRouter
from app.tools.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

class DatabaseBookRouter(BaseBookRouter):
    def __init__(self) -> None:
        super().__init__()
        logger.info("Инициализация DatabaseBookRouter")

    def _setup_routes(self) -> None:
        self.router.add_api_route("/", self.create_book, methods=["POST"], response_model=schema.Book)
        self.router.add_api_route("/", self.read_books, methods=["GET"], response_model=List[schema.Book])
        self.router.add_api_route("/{book_id}", self.read_book, methods=["GET"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.update_book, methods=["PUT"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.delete_book, methods=["DELETE"], response_model=schema.Book)
        logger.debug("Пути базы данных определены")

    async def create_book(self, book: schema.BookCreate, db: AsyncSession = Depends(get_db)) -> schema.Book:
        try:
            logger.info(f"Создание книги: {book.title}")
            created_book = await book_db_crud.create(db=db, obj_in=book)
            logger.info(f"Книга создана по ID: {created_book.id}")
            return created_book
        except Exception as e:
            logger.error(f"Ошибка создания книги: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create book")

    async def read_books(self, skip: int = 0, limit: int = 100,
                        db: AsyncSession = Depends(get_db)) -> List[schema.Book]:
        try:
            logger.debug(f"Извлечение кнги, начиная: {skip}, с ограничением: {limit}")
            books = await book_db_crud.get_multi(db, skip=skip, limit=limit)
            logger.info(f"Извлечено {len(books)} книг")
            return books
        except Exception as e:
            logger.error(f"Ошибка извлечения книг: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch books")

    async def read_book(self, book_id: int, db: AsyncSession = Depends(get_db)) -> schema.Book:
        try:
            logger.info(f"Книга извлечена по ID: {book_id}")
            book = await book_db_crud.get(db, id=book_id)
            if not book:
                logger.warning(f"Книга найдена по ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            return book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка извлечения книги {book_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch book")

    async def update_book(self, book_id: int, book: schema.BookUpdate,
                         db: AsyncSession = Depends(get_db)) -> schema.Book:
        try:
            logger.info(f"Книга обновлена по ID: {book_id}")
            db_book = await book_db_crud.update(db, id=book_id, obj_in=book)
            if not db_book:
                logger.warning(f"Книга для обновления не найдена, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Книга обновлена по ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка обновления книги {book_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update book")

    async def delete_book(self, book_id: int, db: AsyncSession = Depends(get_db)) -> schema.Book:
        try:
            logger.info(f"Удаление книги по ID: {book_id}")
            db_book = await book_db_crud.delete(db, id=book_id)
            if not db_book:
                logger.warning(f"Книга не найдена для удаления, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Book deleted with ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка удаления книги {book_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete book")

db_router = DatabaseBookRouter()
