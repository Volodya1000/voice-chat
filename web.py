# web.py
from fastapi import (
    APIRouter, Request, Depends, Form,
    HTTPException # <-- ДОБАВЛЕНО
)
# --- НОВЫЙ КОД ---
from fastapi.responses import (
    RedirectResponse, HTMLResponse,
    Response, JSONResponse # <-- ИЗМЕНЕНО
)
# Это зависимость из `pip install sse-starlette`
from sse_starlette.sse import EventSourceResponse
import asyncio
# --- КОНЕЦ НОВОГО КОДА ---
from fastapi.templating import Jinja2Templates
from dependency_injector.wiring import inject, Provide
from containers import Container
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
# Импортируем Broadcaster для внедрения в SSE-эндпоинт
from services.chat_service import ChatService, Broadcaster # <-- ИЗМЕНЕНО
from models import MessageType
templates = Jinja2Templates(directory="templates")
router = APIRouter()

COOKIE_NAME = "chat_user_id"

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "error": None})

@router.post("/login")
@inject
async def login(
    request: Request,
    username: str = Form(...),
    password: str | None = Form(None),
    ur: UserRepository = Depends(Provide[Container.user_repo])
):
    user = await ur.ensure_user(username, password)
    redirect = RedirectResponse(url="/chats", status_code=302)
    redirect.set_cookie(COOKIE_NAME, str(user.id), max_age=60*60*24*30, httponly=True)
    return redirect

def get_current_user_id_from_request(request: Request) -> int | None:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        return int(cookie)
    except Exception:
        return None

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
    messages = await mr.get_messages_for_chat(chat_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id, "chats": chats, "selected_chat": chat_id, "messages": messages})

@router.post("/chats/{chat_id}/send")
@inject
async def send_message(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    chat_service: ChatService = Depends(Provide[Container.chat_service])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    await chat_service.process_user_message(chat_id, content)

    return RedirectResponse(url=f"/chats/{chat_id}", status_code=302)

@router.post("/chats/{chat_id}/send")
@inject
async def send_message(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    chat_service: ChatService = Depends(Provide[Container.chat_service])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        # --- ИЗМЕНЕНО ---
        # Для AJAX-запроса (fetch) редирект бесполезен,
        # возвращаем ошибку 401
        raise HTTPException(status_code=401, detail="Not authenticated")
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # Вызываем сервис. Он сам сохранит и опубликует сообщения (USER и MODEL)
    await chat_service.process_user_message(chat_id, content)

    # --- ИЗМЕНЕНО ---
    # Вместо редиректа возвращаем "204 No Content".
    # Клиент (JS) знает, что все прошло успешно.
    return Response(status_code=204)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---


# --- НОВЫЙ ЭНДПОИНТ ДЛЯ SSE ---
@router.get("/chats/{chat_id}/events")
@inject
async def sse_chat_events(
    request: Request,
    chat_id: int,
    # Внедряем наш Singleton Broadcaster
    broadcaster: Broadcaster = Depends(Provide[Container.broadcaster])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Здесь в production-коде нужно проверить,
    # имеет ли `user_id` доступ к `chat_id`,
    # прежде чем подписывать его.

    async def event_generator():
        """Генератор, который слушает очередь и отправляет данные клиенту."""
        queue = await broadcaster.subscribe(chat_id)
        try:
            while True:
                # Ждем новое сообщение из очереди
                message_json = await queue.get()
                # Отправляем его клиенту в формате SSE
                yield {
                    "event": "message", # Имя события (для onmessage в JS)
                    "data": message_json
                }
        except asyncio.CancelledError:
            # Клиент отключился (закрыл вкладку)
            broadcaster.unsubscribe(chat_id, queue)
            raise

    # EventSourceResponse будет держать соединение открытым
    return EventSourceResponse(event_generator())