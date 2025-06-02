from fastapi import APIRouter, HTTPException

from typing import List


from app.schemas import book as schema
from app.crud.jsonbin_book import book_jsonbin_crud

from app.interface.book import BaseBookRouter
from app.tools.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

class JsonBinBookRouter(BaseBookRouter):
    def __init__(self) -> None:
        super().__init__()
        logger.info("Инициализация JsonBinBookRouter")

    def _setup_routes(self) -> None:
        self.router = APIRouter()
        self.router.add_api_route("/", self.create_book, methods=["POST"], response_model=schema.Book)
        self.router.add_api_route("/", self.read_books, methods=["GET"], response_model=List[schema.Book])
        self.router.add_api_route("/{book_id}", self.read_book, methods=["GET"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.update_book, methods=["PUT"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.delete_book, methods=["DELETE"], response_model=schema.Book)
        logger.debug("Настройка маршрутов для работы с JsonBin завершена")

    async def create_book(self, book: schema.BookCreate) -> schema.Book:
        try:
            logger.info(f"Создание книги в JsonBin: {book.title}")
            created_book = await book_jsonbin_crud.create(obj_in=book)
            logger.info(f"Книга создана в JsonBin с ID: {created_book.id}")
            return created_book
        except Exception as e:
            logger.error(f"Ощшибка создания книги в JsonBin: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create book in JsonBin")

    async def read_books(self, skip: int = 0, limit: int = 100) -> List[schema.Book]:
        try:
            logger.debug(f"Извлечение книг из JsonBin, пропуск: {skip}, лимит: {limit}")
            books = await book_jsonbin_crud.get_multi(skip=skip, limit=limit)
            logger.info(f"Извлечение {len(books)} книг из JsonBin")
            return books
        except Exception as e:
            logger.error(f"Ошибка извлечения книг из JsonBin: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch books from JsonBin")

    async def read_book(self, book_id: int) -> schema.Book:
        try:
            logger.info(f"Извлечение книги из JsonBin с ID: {book_id}")
            book = await book_jsonbin_crud.get(id=book_id)
            if not book:
                logger.warning(f"Книга не найдена в JsonBin с ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            return book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка извлечения книги {book_id} из JsonBin: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch book from JsonBin")

    async def update_book(self, book_id: int, book: schema.BookUpdate) -> schema.Book:
        try:
            logger.info(f"Обновление книги в JsonBin с ID: {book_id}")
            db_book = await book_jsonbin_crud.update(id=book_id, obj_in=book)
            if not db_book:
                logger.warning(f"Книга не найдена в JsonBin для обновления, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Книга обновлена в JsonBin с ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка обновления книги {book_id} в JsonBin: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update book in JsonBin")

    async def delete_book(self, book_id: int) -> schema.Book:
        try:
            logger.info(f"Удаление книги в JsonBin с ID: {book_id}")
            db_book = await book_jsonbin_crud.delete(id=book_id)
            if not db_book:
                logger.warning(f"Книга не найдена в JsonBin для удаления, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Книга удалена в JsonBin с ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка удаления книги {book_id} в JsonBin: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete book from JsonBin")

jsonbin_router = JsonBinBookRouter()
