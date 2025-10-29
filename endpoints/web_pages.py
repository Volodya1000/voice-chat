# endpoints/web_pages.py
from datetime import datetime
from fastapi import (
    APIRouter, Request, Depends, Form
)
from fastapi.responses import (
    RedirectResponse, HTMLResponse
)
from fastapi.templating import Jinja2Templates
from dependency_injector.wiring import inject, Provide
from containers import Container
from dtos import MessageDTO
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
from typing import Optional
from .utils import get_current_user_id_from_request, COOKIE_NAME

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "error": None})

@router.post("/login")
@inject
async def login(
    request: Request,
    username: str = Form(...),
    password: Optional[str] = Form(None),
    ur: UserRepository = Depends(Provide[Container.user_repo])
):
    user = await ur.ensure_user(username, password)
    redirect = RedirectResponse(url="/chats", status_code=302)
    redirect.set_cookie(COOKIE_NAME, str(user.id), max_age=60*60*24*30, httponly=True)
    return redirect

@router.get("/logout")
async def logout(request: Request):
    r = RedirectResponse(url="/", status_code=302)
    r.delete_cookie(COOKIE_NAME)
    return r

@router.get("/chats", response_class=HTMLResponse)
@inject
async def chats_page(
    request: Request,
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    chats = await cr.list_chats_for_user(user_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id, "chats": chats, "selected_chat": None, "messages": []})

@router.post("/chats/new")
@inject
async def create_chat(
    request: Request,
    title: str = Form(...),
    cr: ChatRepository = Depends(Provide[Container.chat_repo])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    await cr.create_chat(user_id=user_id, title=title)
    return RedirectResponse(url="/chats", status_code=302)

@router.get("/chats/{chat_id}", response_class=HTMLResponse)
@inject
async def open_chat(
    request: Request,
    chat_id: int,
    cr: ChatRepository = Depends(Provide[Container.chat_repo]),
    mr: MessageRepository = Depends(Provide[Container.message_repo])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    chats = await cr.list_chats_for_user(user_id)
    messages_raw = await mr.get_messages_for_chat(chat_id)  # SQLAlchemy objects

    # Pydantic модели для серверного рендера (с datetime)
    messages_for_render = [MessageDTO.model_validate(m) for m in messages_raw]

    # JSON-safe словари для JS (datetime -> ISO строки и т.д.)
    initial_messages = [
        {
            "id": m.id,
            "content": m.content,
            "message_type": m.message_type.value,
            "created_at": m.created_at.isoformat() if isinstance(m.created_at, datetime) else str(m.created_at),
        }
        for m in messages_for_render
    ]

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user_id": user_id,
            "chats": chats,
            "selected_chat": chat_id,
            # messages — оставляем для partials/messages.html (ожидает datetime)
            "messages": messages_for_render,
            # initial_messages — для вставки в JS
            "initial_messages": initial_messages,
        }
    )