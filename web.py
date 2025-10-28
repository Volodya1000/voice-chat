from fastapi import (
    APIRouter, Request, Depends, Form,
    HTTPException,BackgroundTasks, UploadFile, File # <-- ИСПРАВЛЕНО
)
# --- НОВЫЙ КОД ---
from fastapi.responses import (
    RedirectResponse, HTMLResponse,
    Response, JSONResponse
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
from services.chat_service import ChatService, Broadcaster 
from services.transcription_service import TranscriptionService # <-- ИМПОРТ СЕРВИСА
from models import MessageType
from typing import Optional # <-- ДОБАВЛЕНО для type hinting

templates = Jinja2Templates(directory="templates")
router = APIRouter()

COOKIE_NAME = "chat_user_id"

# ---------------------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ ЭКЗЕМПЛЯРА СЕРВИСА
# В рабочей архитектуре Dependency Injector (DI) это должно делаться в containers.py
# ---------------------------------------------------------------------
transcription_service_instance = TranscriptionService()

def get_current_user_id_from_request(request: Request) -> Optional[int]: # <-- ИСПРАВЛЕН ТИП (int | None)
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        return int(cookie)
    except Exception:
        return None

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "error": None})

@router.post("/login")
@inject
async def login(
    request: Request,
    username: str = Form(...),
    password: Optional[str] = Form(None), # <-- ИСПРАВЛЕН ТИП
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
    messages = await mr.get_messages_for_chat(chat_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id, "chats": chats, "selected_chat": chat_id, "messages": messages})

@router.post("/chats/{chat_id}/send")
@inject
async def send_message(
        request: Request,
        chat_id: int,
        background_tasks: BackgroundTasks, 
        content: str = Form(...),
        chat_service: ChatService = Depends(Provide[Container.chat_service])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    background_tasks.add_task(
        chat_service.process_user_message,
        chat_id=chat_id,
        content=content,
        user_id=user_id
    )

    return Response(status_code=204)

# ---------------------------------------------------------------------
# ЭНДПОИНТ ДЛЯ ТРАНСКРИПЦИИ АУДИО
# ---------------------------------------------------------------------
@router.post("/chats/transcribe_voice")
async def transcribe_voice(
        request: Request,
        audio_file: UploadFile = File(...),
        transcription_service: TranscriptionService = Depends(lambda: transcription_service_instance)
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Проверка MIME-типа
    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an audio file.")

    try:
        # Вызов сервиса транскрипции
        user_prompt = await transcription_service.transcribe_audio(audio_file)

        # Возвращаем транскрибированный текст на фронтенд
        return JSONResponse({"content": user_prompt})
    except HTTPException as e:
        raise e
    except Exception as e:
        # В случае не-HTTPException ошибок
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Критическая ошибка обработки аудио: {e}")


# --- ОБНОВЛЕННЫЙ ЭНДПОИНТ SSE ---
@router.get("/chats/{chat_id}/events")
@inject
async def sse_chat_events(
        request: Request,
        chat_id: int,
        broadcaster: Broadcaster = Depends(Provide[Container.broadcaster])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def event_generator():
        """Генератор, который слушает очередь и отправляет данные клиенту."""
        queue = await broadcaster.subscribe(chat_id)
        try:
            while True:
                # Ждем новое событие (словарь) из очереди
                event_data_dict = await queue.get()

                # event_data_dict УЖЕ имеет формат {"event": "...", "data": "..."}
                yield event_data_dict

        except asyncio.CancelledError:
            # Клиент отключился
            broadcaster.unsubscribe(chat_id, queue)
            raise

    return EventSourceResponse(event_generator())