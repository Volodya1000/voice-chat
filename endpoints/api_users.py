# endpoints/api_users.py
from fastapi import APIRouter, Depends, HTTPException
# 1. Импортируем 'inject' и 'Provide'
from dependency_injector.wiring import inject, Provide

from dtos import (
    UserCreateDTO,
    UserDTO,
    ChatCreateDTO,
    ChatDTO,
)
# 2. Импортируем наш контейнер и типы репозиториев
from containers import Container
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository


# Обратите внимание на префикс роутера
router = APIRouter(prefix="/api/users")

@router.post("", response_model=UserDTO) # <--- Путь изменен на ""
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

@router.get("/{user_id}", response_model=UserDTO) # <--- Путь изменен
@inject
async def get_user(
    user_id: int,
    ur: UserRepository = Depends(Provide[Container.user_repo])
):
    user = await ur.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return UserDTO.model_validate(user)

@router.post("/{user_id}/chats", response_model=ChatDTO) # <--- Путь изменен
@inject
async def create_chat_for_user(
    user_id: int,
    payload: ChatCreateDTO,
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    chat = await cr.create_chat(user_id=user_id, title=payload.title)
    return ChatDTO.model_validate(chat)

@router.get("/{user_id}/chats", response_model=list[ChatDTO]) # <--- Путь изменен
@inject
async def list_chats(
    user_id: int,
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    chats = await cr.list_chats_for_user(user_id)
    return [ChatDTO.model_validate(c) for c in chats]