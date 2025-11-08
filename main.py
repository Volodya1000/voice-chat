# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from db import init_db
from containers import container

from endpoints import (
    web_pages,
    web_actions,
    api_users,
    api_messages,
    api_documents,
)
import services.chat_service as chat_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Async Chat App with DTOs & Repositories", lifespan=lifespan)

container.wire(modules=[
    web_pages,
    web_actions,
    api_users,
    api_messages,
    api_documents,
    chat_service,
])

for router in [
    web_pages.router,
    web_actions.router,
    api_users.router,
    api_messages.router,
    api_documents.router,
]:
    app.include_router(router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
