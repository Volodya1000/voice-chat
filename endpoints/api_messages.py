# endpoints/api_messages.py
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide

from dtos import (
    MessageCreateDTO,
    MessageDTO,
)
from containers import Container
from repositories.message_repo import MessageRepository
from models import MessageType

# Обратите внимание на префикс роутера
router = APIRouter(prefix="/api/chats")


@router.post("/{chat_id}/messages", response_model=MessageDTO) # <--- Путь изменен
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

@router.get("/{chat_id}/messages", response_model=list[MessageDTO]) # <--- Путь изменен
@inject
async def get_messages(
    chat_id: int,
    mr: MessageRepository = Depends(Provide[Container.message_repo])
):
    msgs = await mr.get_messages_for_chat(chat_id)
    return [MessageDTO.model_validate(m) for m in msgs]