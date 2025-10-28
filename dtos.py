from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageTypeStr(str, Enum):
    USER = "user"
    MODEL = "model"

# ======================
# Input DTOs
# ======================

class UserCreateDTO(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: Optional[str] = None

class ChatCreateDTO(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class MessageCreateDTO(BaseModel):
    content: str = Field(..., min_length=1)
    message_type: MessageTypeStr = MessageTypeStr.USER

# ======================
# Output DTOs
# ======================

class MessageDTO(BaseModel):
    id: int
    content: str
    message_type: MessageTypeStr
    created_at: datetime

    model_config = {"from_attributes": True}

class ChatDTO(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageDTO] = []

    model_config = {"from_attributes": True}

class UserDTO(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}
