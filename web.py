# web.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
from models import MessageType
from services.chat_service import ChatService

templates = Jinja2Templates(directory="templates")
router = APIRouter()

COOKIE_NAME = "chat_user_id"

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # логин-страница
    return templates.TemplateResponse("index.html", {"request": request, "error": None})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str | None = Form(None), session: AsyncSession = Depends(get_session)):
    ur = UserRepository(session)
    user = await ur.ensure_user(username, password)
    redirect = RedirectResponse(url="/chats", status_code=302)
    # ставим cookie с user_id, чтобы не просить логин при перезапусках приложения
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
async def chats_page(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    cr = ChatRepository(session)
    chats = await cr.list_chats_for_user(user_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id, "chats": chats, "selected_chat": None, "messages": []})

@router.post("/chats/new")
async def create_chat(request: Request, title: str = Form(...), session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    cr = ChatRepository(session)
    await cr.create_chat(user_id=user_id, title=title)
    return RedirectResponse(url="/chats", status_code=302)

@router.get("/chats/{chat_id}", response_class=HTMLResponse)
async def open_chat(request: Request, chat_id: int, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    cr = ChatRepository(session)
    mr = MessageRepository(session)
    chats = await cr.list_chats_for_user(user_id)
    messages = await mr.get_messages_for_chat(chat_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id, "chats": chats, "selected_chat": chat_id, "messages": messages})

@router.post("/chats/{chat_id}/send")
async def send_message(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    mr = MessageRepository(session)
    chat_service = ChatService(message_repo=mr)
    await chat_service.process_user_message(chat_id, content)

    return RedirectResponse(url=f"/chats/{chat_id}", status_code=302)
