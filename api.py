# api.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
# 1. Импортируем 'inject' и 'Provide'
from dependency_injector.wiring import inject, Provide

from dtos import (
    UserCreateDTO,
    UserDTO,
    ChatCreateDTO,
    ChatDTO,
    MessageCreateDTO,
    MessageDTO,
    MessageTypeStr,
)
# 2. Импортируем наш контейнер и типы репозиториев
from containers import Container
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
from models import MessageType

router = APIRouter(prefix="/api")

@router.post("/users", response_model=UserDTO)
@inject
async def create_user(
    payload: UserCreateDTO,
    ur: UserRepository = Depends(Provide[Container.user_repo])
):
    existing = await ur.get_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="username exists")
    user = await ur.create_user(payload.username, payload.password)
    return UserDTO.model_validate(user)

@router.get("/users/{user_id}", response_model=UserDTO)
@inject
async def get_user(
    user_id: int,
    ur: UserRepository = Depends(Provide[Container.user_repo])
):
    user = await ur.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return UserDTO.model_validate(user)

@router.post("/users/{user_id}/chats", response_model=ChatDTO)
@inject
async def create_chat_for_user(
    user_id: int,
    payload: ChatCreateDTO,
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    chat = await cr.create_chat(user_id=user_id, title=payload.title)
    return ChatDTO.model_validate(chat)

@router.get("/users/{user_id}/chats", response_model=list[ChatDTO])
@inject
async def list_chats(
    user_id: int,
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    chats = await cr.list_chats_for_user(user_id)
    return [ChatDTO.model_validate(c) for c in chats]

@router.post("/chats/{chat_id}/messages", response_model=MessageDTO)
@inject
async def add_message(
    chat_id: int,
    payload: MessageCreateDTO,
    mr: MessageRepository = Depends(Provide[Container.message_repo])
):
    try:
        mtype = MessageType(payload.message_type.value)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid message_type")
    msg = await mr.add_message(chat_id=chat_id, content=payload.content, message_type=mtype)
    return MessageDTO.model_validate(msg)

@router.get("/chats/{chat_id}/messages", response_model=list[MessageDTO])
@inject
async def get_messages(
    chat_id: int,
    mr: MessageRepository = Depends(Provide[Container.message_repo])
):
    msgs = await mr.get_messages_for_chat(chat_id)
    return [MessageDTO.model_validate(m) for m in msgs]