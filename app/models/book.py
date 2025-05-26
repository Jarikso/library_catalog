from sqlalchemy import Column, Integer, String, Boolean, Text, Float
from ..database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    year = Column(Integer)
    genre = Column(String)
    pages = Column(Integer)
    available = Column(Boolean, default=True)
    # поля заполняются из Open Library
    cover_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)