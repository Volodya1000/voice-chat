# main.py
import uvicorn
from fastapi import FastAPI
from db import init_db
from api import router as api_router
from web import router as web_router
from fastapi.staticfiles import StaticFiles
from containers import container
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Async Chat App with DTOs & Repositories", lifespan=lifespan)

# Подключаем контейнер к модулям.
# Это необходимо, чтобы декоратор @inject заработал.
container.wire(modules=["api", "web", "services.chat_service"])

app.include_router(api_router)
app.include_router(web_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)