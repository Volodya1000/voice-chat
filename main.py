# main.py
import uvicorn
from fastapi import FastAPI
from db import init_db
from api import router as api_router
from web import router as web_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Async Chat App with DTOs & Repositories")

# Подключаем роутеры
app.include_router(api_router)
app.include_router(web_router)

# Статика
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    await init_db()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
