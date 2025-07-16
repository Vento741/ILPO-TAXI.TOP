"""
УМНЫЙ ТАКСОПАРК - FastAPI Backend
Главный файл приложения с подключением роутеров и OpenRouter API интеграцией
"""

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import os

# Импортируем роутеры
from routers.main_routes import main_router
from routers.chat_routes import chat_router

# Создаем приложение FastAPI
app = FastAPI(
    title="ILPO-TAXI - Умный Таксопарк API",
    description="API для первого умного таксопарка с ИИ-консультантом (OpenRouter + gpt-4o-mini-search-preview)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем шаблоны (пока не используется, но готово для будущего)
templates = Jinja2Templates(directory=".")

# Подключаем роутеры
app.include_router(main_router, tags=["main"])
app.include_router(chat_router, tags=["chat"])

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = datetime.now() - start_time
    
    print(f"📊 {request.method} {request.url} - {response.status_code} - {process_time.total_seconds():.3f}s")
    return response

# Добавляем информационные endpoints
@app.get("/api/info")
async def get_api_info():
    """Информация о API"""
    return {
        "name": "ILPO-TAXI Умный Таксопарк API",
        "version": "2.0.0",
        "description": "Первый в России умный таксопарк с ИИ-консультантом",
        "features": [
            "OpenRouter API интеграция",
            "gpt-4o-mini-search-preview модель",
            "WebSocket чат в реальном времени",
            "Управление сессиями",
            "Аналитика разговоров"
        ],
        "endpoints": {
            "chat": "/ws/chat",
            "docs": "/docs",
            "health": "/api/chat/health"
        },
        "ai_model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini-search-preview"),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Запуск сервера Умного Таксопарка...")
    print("📱 Сайт будет доступен по адресу: http://localhost:8000")
    print("🤖 WebSocket чат: ws://localhost:8000/ws/chat")
    print("📋 API документация: http://localhost:8000/docs")
    print("🧠 ИИ модель:", os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini-search-preview"))
    print("🔧 Режим отладки:", os.getenv("DEBUG", "True"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 