# models.py
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class MessageType(enum.Enum):
    USER = "user"
    MODEL = "model"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(256), nullable=True)  # можно хранить хэш (опционально)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="chats", lazy="joined")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", lazy="selectin", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)

    chat = relationship("Chat", back_populates="messages", lazy="joined")
