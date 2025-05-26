from typing import Optional
from pydantic import BaseModel

class BookBase(BaseModel):
    title: str
    author: str
    year: int
    genre: str
    pages: int
    available: bool = True
    cover_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    pages: Optional[int] = None
    available: Optional[bool] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Название книги",
                "author": "Автор",
                "year": 2023,
                "genre": "Жанр",
                "pages": 300,
                "available": True,
                "cover_url": "https://covers.openlibrary.org/b/id/12345-M.jpg",
                "description": "Интересное описание книги",
                "rating": 4.5
            }
        }