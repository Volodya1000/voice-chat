# endpoints/utils.py
from fastapi import Request
from typing import Optional

COOKIE_NAME = "chat_user_id"

def get_current_user_id_from_request(request: Request) -> Optional[int]:
    """
    Извлекает ID пользователя из cookie 'chat_user_id'.
    """
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        return int(cookie)
    except Exception:
        return None