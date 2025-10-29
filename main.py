# main.py
import uvicorn
from fastapi import FastAPI
from db import init_db
# --- ИЗМЕНЕНИЯ ---
# Импортируем роутеры из новой директории
from endpoints.web_pages import router as web_pages_router
from endpoints.web_actions import router as web_actions_router
from endpoints.api_users import router as api_users_router
from endpoints.api_messages import router as api_messages_router
# --- КОНЕЦ ИЗМЕНЕНИЙ ---

from fastapi.staticfiles import StaticFiles
from containers import container
from contextlib import asynccontextmanager

# --- ИЗМЕНЕНИЯ ---
# Импортируем модули для 'wire'
import endpoints.web_pages as web_pages_module
import endpoints.web_actions as web_actions_module
import endpoints.api_users as api_users_module
import endpoints.api_messages as api_messages_module
# --- КОНЕЦ ИЗМЕНЕНИЙ ---

import services.chat_service as chat_service_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Async Chat App with DTOs & Repositories", lifespan=lifespan)

# Подключаем контейнер к модулям.
# Это необходимо, чтобы декоратор @inject заработал.
# --- ИЗМЕНЕНИЯ ---
container.wire(modules=[
    web_pages_module,
    web_actions_module,
    api_users_module,
    api_messages_module,
    chat_service_module
])

# Включаем все наши разделенные роутеры
app.include_router(web_pages_router)
app.include_router(web_actions_router)
app.include_router(api_users_router)
app.include_router(api_messages_router)
# --- КОНЕЦ ИЗМЕНЕНИЙ ---

app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)