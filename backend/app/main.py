#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, businesses, audit, monitoring, chat  # Добавлен chat

# Создаём таблицы в БД
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SaaDvisor API",
    description="API для цифрового советника бизнеса",
    version="1.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(businesses.router)
app.include_router(audit.router)
app.include_router(monitoring.router)
app.include_router(chat.router)  # Добавлен роутер чата


@app.get("/")
def root():
    return {
        "message": "SaaDvisor API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/auth/register",
            "/auth/login",
            "/businesses",
            "/audit/{business_id}",
            "/chat/send",
            "/chat/business/{business_id}/context"
        ]
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}