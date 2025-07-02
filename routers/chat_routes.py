"""
УМНЫЙ ТАКСОПАРК - Роутеры для чата
WebSocket роутеры для ИИ-консультанта с OpenRouter API интеграцией
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# Импорты наших сервисов
from services.openrouter_ai import openrouter_ai
from services.chat_manager import chat_manager

# Создаем роутер для чата
chat_router = APIRouter()

# Инициализация менеджера чата при запуске приложения
@chat_router.on_event("startup")
async def startup_event():
    """Инициализация сервисов при запуске"""
    print("🚀 Инициализация чат-сервисов...")
    await chat_manager.initialize()
    print("✅ Чат-сервисы успешно инициализированы")

# Список активных WebSocket соединений
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_sessions: Dict[WebSocket, str] = {}  # Связь между WebSocket и session_id
    
    async def connect(self, websocket: WebSocket, session_id: str = None):
        await websocket.accept()
        
        # Создаем или получаем сессию
        if not session_id:
            session_id = await chat_manager.create_session()
        
        self.active_connections[session_id] = websocket
        self.connection_sessions[websocket] = session_id
        
        print(f"🔗 Новое WebSocket соединение для сессии {session_id}. Всего: {len(self.active_connections)}")
        
        return session_id
    
    def disconnect(self, websocket: WebSocket):
        session_id = self.connection_sessions.get(websocket)
        if session_id and session_id in self.active_connections:
            del self.active_connections[session_id]
        if websocket in self.connection_sessions:
            del self.connection_sessions[websocket]
        
        print(f"❌ WebSocket соединение закрыто для сессии {session_id}. Осталось: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
    
    async def send_to_session(self, session_id: str, message: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await self.send_personal_message(message, websocket)
    
    async def broadcast(self, message: str):
        for websocket in self.active_connections.values():
            await self.send_personal_message(message, websocket)

# Создаем экземпляр менеджера соединений
manager = ConnectionManager()

@chat_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, session_id: str = Query(None)):
    """WebSocket endpoint для чата с ИИ-консультантом"""
    
    # Подключаемся и получаем session_id
    session_id = await manager.connect(websocket, session_id)
    
    # Отправляем приветственное сообщение
    welcome_message = {
        "type": "ai_message",
        "content": "Привет! 👋 Я ИИ-консультант ILPO-TAXI. Помогу с подключением к Яндекс.Такси и Доставке. Что вас интересует?",
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "model": "OpenRouter AI (gpt-4o-mini-search-preview)"
    }
    
    # Добавляем приветственное сообщение в историю
    await chat_manager.add_message(
        session_id, 
        "assistant", 
        welcome_message["content"],
        timestamp=welcome_message["timestamp"]
    )
    
    await manager.send_personal_message(json.dumps(welcome_message), websocket)
    
    try:
        while True:
            # Получаем сообщение от пользователя
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("content", "").strip()
            if not user_message:
                continue
            
            print(f"💬 Получено сообщение в сессии {session_id}: {user_message}")
            
            # Добавляем сообщение пользователя в историю
            await chat_manager.add_message(session_id, "user", user_message)
            
            # Отправляем индикатор "печатает"
            typing_message = {
                "type": "typing",
                "content": "ИИ-консультант печатает...",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(json.dumps(typing_message), websocket)
            
            # Получаем историю разговора
            conversation_history = await chat_manager.get_conversation_history(session_id, limit=10)
            
            # Генерируем умный ответ через OpenRouter API
            ai_response_data = await openrouter_ai.get_smart_response(
                user_message, 
                context={
                    "session_id": session_id,
                    "conversation_history": conversation_history
                }
            )
            
            # Формируем ответное сообщение
            response_message = {
                "type": "ai_message",
                "content": ai_response_data["content"],
                "timestamp": ai_response_data["timestamp"],
                "intent": ai_response_data["intent"],
                "processing_time": ai_response_data["processing_time"],
                "model": ai_response_data["model"],
                "session_id": session_id
            }
            
            # Добавляем ответ ИИ в историю
            await chat_manager.add_message(
                session_id, 
                "assistant", 
                ai_response_data["content"],
                timestamp=ai_response_data["timestamp"],
                intent=ai_response_data["intent"],
                processing_time=ai_response_data["processing_time"]
            )
            
            # Отправляем ответ пользователю
            await manager.send_personal_message(json.dumps(response_message), websocket)
            
    except WebSocketDisconnect:
        print(f"📱 Пользователь отключился от сессии {session_id}")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ Ошибка WebSocket в сессии {session_id}: {e}")
        manager.disconnect(websocket)

@chat_router.get("/api/chat/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Получить статистику сессии чата"""
    stats = await chat_manager.get_session_stats(session_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    return JSONResponse(content=stats)

@chat_router.get("/api/chat/sessions")
async def get_all_sessions_stats():
    """Получить общую статистику по всем сессиям"""
    stats = await chat_manager.get_all_sessions_stats()
    return JSONResponse(content=stats)

@chat_router.post("/api/chat/sessions/{session_id}/export")
async def export_session(session_id: str):
    """Экспортировать сессию чата"""
    success = await chat_manager.export_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Сессия не найдена или ошибка экспорта")
    
    return JSONResponse(content={"message": "Сессия успешно экспортирована"})

@chat_router.post("/api/chat/test")
async def test_ai_response(message: str):
    """Тестовый endpoint для проверки OpenRouter AI"""
    try:
        response = await openrouter_ai.get_smart_response(message)
        return JSONResponse(content={
            "success": True,
            "response": response
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@chat_router.get("/api/chat/health")
async def chat_health_check():
    """Проверка здоровья чат-сервиса"""
    try:
        # Тестируем OpenRouter API
        test_response = await openrouter_ai.generate_response("Тест")
        
        # Получаем статистику
        stats = await chat_manager.get_all_sessions_stats()
        
        return JSONResponse(content={
            "status": "healthy",
            "openrouter_api": "working" if test_response else "error",
            "active_sessions": stats.get("active_sessions", 0),
            "total_sessions": stats.get("total_sessions", 0),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Обработка завершения работы
@chat_router.on_event("shutdown")
async def shutdown_event():
    """Корректное завершение работы сервисов"""
    print("🔄 Завершение работы чат-сервиса...")
    
    # Закрываем менеджер чата
    await chat_manager.shutdown()
    
    # Закрываем OpenRouter AI клиент
    await openrouter_ai.close()
    
    print("✅ Чат-сервис корректно завершен") 