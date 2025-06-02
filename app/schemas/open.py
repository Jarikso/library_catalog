from typing import Optional
from pydantic import BaseModel

class OpenLibraryBookInfo(BaseModel):
    cover_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    first_publish_year: Optional[int] = None