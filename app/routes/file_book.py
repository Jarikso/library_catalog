from fastapi import APIRouter, HTTPException

from typing import List
from app.schemas import book as schema
from app.crud.file_book import book_file_crud

from app.interface.book import BaseBookRouter
from app.tools.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

class FileBookRouter(BaseBookRouter):
    def __init__(self) -> None:
        super().__init__()
        logger.info("Инициализация FileBookRouter")

    def _setup_routes(self) -> None:
        self.router.add_api_route("/", self.create_book, methods=["POST"], response_model=schema.Book)
        self.router.add_api_route("/", self.read_books, methods=["GET"], response_model=List[schema.Book])
        self.router.add_api_route("/{book_id}", self.read_book, methods=["GET"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.update_book, methods=["PUT"], response_model=schema.Book)
        self.router.add_api_route("/{book_id}", self.delete_book, methods=["DELETE"], response_model=schema.Book)
        logger.debug("Настройка маршрутов для работы с файлами завершена")

    async def create_book(self, book: schema.BookCreate) -> schema.Book:
        try:
            logger.info(f"Запись книги в файл: {book.title}")
            created_book = await book_file_crud.create(obj_in=book)
            logger.info(f"Книга запса с файл по ID: {created_book.id}")
            return created_book
        except Exception as e:
            logger.error(f"Ошибка записи книги в файл: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create book in file")

    async def read_books(self, skip: int = 0, limit: int = 100) -> List[schema.Book]:
        try:
            logger.debug(f"Извлечение книг из файлов, пропуск: {skip}, ограничение: {limit}")
            books = await book_file_crud.get_multi(skip=skip, limit=limit)
            logger.info(f"Извлечение {len(books)} книги из файла")
            return books
        except Exception as e:
            logger.error(f"Ошибка извлечения книги из файла: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch books from file")

    async def read_book(self, book_id: int) -> schema.Book:
        try:
            logger.info(f"Извлечение книги из файла по ID: {book_id}")
            book = await book_file_crud.get(id=book_id)
            if not book:
                logger.warning(f"Книга не найдена по ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            return book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка извлечения книги {book_id} из файла: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch book from file")

    async def update_book(self, book_id: int, book: schema.BookUpdate) -> schema.Book:
        try:
            logger.info(f"Обновление книги в файле по ID: {book_id}")
            db_book = await book_file_crud.update(id=book_id, obj_in=book)
            if not db_book:
                logger.warning(f"Книги не найдена в файле, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Данные о книге обновлены в файле ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка обновления книги {book_id} в файле: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update book in file")

    async def delete_book(self, book_id: int) -> schema.Book:
        try:
            logger.info(f"Удаление книги в файле ID: {book_id}")
            db_book = await book_file_crud.delete(id=book_id)
            if not db_book:
                logger.warning(f"Книга не найдена в файле, ID: {book_id}")
                raise HTTPException(status_code=404, detail="Книга не найдена")
            logger.info(f"Книга удалена из файла ID: {book_id}")
            return db_book
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка удаления книги {book_id} из файла: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete book from file")

file_router = FileBookRouter()
