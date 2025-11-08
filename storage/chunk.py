# schemas.py
from typing import List, Optional
from pydantic import BaseModel


class Chunk(BaseModel):
    embedding: List[float]
    text: str
    chat_id: int
    doc_id: Optional[str] = None
    doc_name: Optional[str] = None
