"""
УМНЫЙ ТАКСОПАРК - Роутеры для чата
WebSocket роутеры для ИИ-консультанта с OpenRouter API интеграцией
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict
from fastapi import Request
import json
import asyncio


# Импорты наших сервисов
from services.chat_manager import chat_manager
from services.openrouter_ai import OpenRouterAI
from telegram_bot.config.settings import settings

import logging
logger = logging.getLogger(__name__)

# Создаем роутер для чата
chat_router = APIRouter()

# Глобальный экземпляр OpenRouterAI (будет инициализирован при старте)
openrouter_ai: OpenRouterAI = None

# Инициализация менеджера чата при запуске приложения
@chat_router.on_event("startup")
async def startup_event():
    """Инициализация сервисов при запуске"""
    print("🚀 Инициализация чат-сервисов...")
    await chat_manager.initialize()
    
    global openrouter_ai
    openrouter_ai = OpenRouterAI(
        api_key_consultant=settings.OPENROUTER_API_KEY_CONSULTANT,
        api_key_search=settings.OPENROUTER_API_KEY_SEARCH,
        base_url=settings.OPENROUTER_BASE_URL
    )
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
        else:
            # Проверяем, существует ли сессия с данным ID
            existing_session = await chat_manager.get_session(session_id)
            if not existing_session:
                print(f"⚠️ Сессия {session_id} не найдена, создаем новую")
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
    
    # Настройки для стабильности соединения
    websocket.ping_timeout = 60  # Таймаут ping в секундах
    websocket.ping_interval = 30  # Интервал ping в секундах
    
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
            
            message_type = message_data.get("type", "")
            
            # Обработка ping для поддержания соединения
            if message_type == "ping":
                pong_message = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(pong_message), websocket)
                continue
            
            # Обработка обычных сообщений
            if message_type != "user_message":
                continue
                
            user_message = message_data.get("content", "").strip()
            if not user_message:
                continue
            
            print(f"💬 Получено сообщение в сессии {session_id}: {user_message}")
            
            # Проверяем, передан ли чат менеджеру
            from telegram_bot.services.manager_service import manager_service
            
            # Ищем активный чат поддержки для этой сессии
            web_chat_id = f"web_{session_id}"
            support_chat = await check_if_transferred_to_manager(session_id)
            
            if support_chat and support_chat.is_active:
                # Чат передан менеджеру - пересылаем сообщение
                success = await manager_service.send_message_to_manager(
                    chat_id=support_chat.chat_id,
                    message_text=user_message,
                    client_name=support_chat.client_name
                )
                
                if success:
                    # Добавляем сообщение пользователя в историю
                    await chat_manager.add_message(session_id, "user", user_message)
                    
                    # Отправляем подтверждение пользователю
                    confirmation_message = {
                        "type": "system_message",
                        "content": "✅ Ваше сообщение отправлено менеджеру. Ожидайте ответа.",
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id
                    }
                    await manager.send_personal_message(json.dumps(confirmation_message), websocket)
                else:
                    # Ошибка отправки
                    error_message = {
                        "type": "system_message",
                        "content": "❌ Не удалось отправить сообщение менеджеру. Попробуйте позже.",
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id
                    }
                    await manager.send_personal_message(json.dumps(error_message), websocket)
                
                continue  # Не обрабатываем через ИИ
            
            # Чат не передан менеджеру - обычная обработка через ИИ
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
            
            # Отладочная информация для длинных сообщений
            content_length = len(ai_response_data["content"])
            print(f"📤 Отправляем ответ: {content_length} символов")
            if content_length > 1000:
                print(f"🔍 Первые 200 символов: {ai_response_data['content'][:200]}...")
                print(f"🔍 Последние 200 символов: ...{ai_response_data['content'][-200:]}")
            
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
            try:
                json_message = json.dumps(response_message, ensure_ascii=False)
                print(f"📡 Размер JSON сообщения: {len(json_message)} байт")
                await manager.send_personal_message(json_message, websocket)
                print("✅ Сообщение успешно отправлено через WebSocket")
            except Exception as send_error:
                print(f"❌ Ошибка отправки WebSocket сообщения: {send_error}")
                # Попробуем отправить сокращенную версию
                short_content = ai_response_data["content"][:1000] + "...\n\n[Сообщение сокращено]"
                short_response = response_message.copy()
                short_response["content"] = short_content
                await manager.send_personal_message(json.dumps(short_response, ensure_ascii=False), websocket)
            
    except WebSocketDisconnect:
        print(f"📱 Пользователь отключился от сессии {session_id}")
        manager.disconnect(websocket)
    except ConnectionResetError:
        print(f"🔌 Соединение сброшено для сессии {session_id}")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ Ошибка WebSocket в сессии {session_id}: {e}")
        try:
            # Пытаемся отправить сообщение об ошибке клиенту
            error_message = {
                "type": "error",
                "content": "Произошла ошибка на сервере. Попробуйте переподключиться.",
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(json.dumps(error_message), websocket)
        except:
            pass  # Если не удалось отправить, просто игнорируем
        finally:
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

@chat_router.post("/api/chat/transfer-to-manager")
async def transfer_to_manager(request: Request):
    """Переключение веб-чата на живого менеджера"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        chat_history = data.get("chat_history", [])
        client_name = data.get("client_name")
        client_phone = data.get("client_phone")
        
        if not session_id:
            return {"success": False, "error": "session_id обязательный"}
        
        # Импортируем сервис менеджеров
        from telegram_bot.services.manager_service import manager_service
        
        # Создаем чат поддержки с сохранением истории
        chat_data = await manager_service.create_support_chat(
            session_id=session_id,
            chat_history=chat_history,
            client_name=client_name,
            client_phone=client_phone
        )
        
        if not chat_data:
            return {
                "success": False,
                "error": "Нет доступных менеджеров",
                "message": "Все менеджеры заняты. Оставьте заявку на сайте, мы свяжемся с вами."
            }
        
        # Отправляем уведомление менеджеру
        await manager_service.notify_manager_new_chat_by_data(
            manager_telegram_id=chat_data["manager_telegram_id"],
            chat_data=chat_data,
            chat_history=chat_history
        )
        
        return {
            "success": True,
            "message": "Менеджер подключен!",
            "manager_name": chat_data["manager_name"],
            "chat_id": chat_data["chat_id"],
            "support_chat_id": chat_data["id"]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка переключения на менеджера: {e}")
        return {
            "success": False,
            "error": "Внутренняя ошибка сервера"
        }

@chat_router.post("/api/chat/send-message")
async def send_message_to_support(request: Request):
    """Отправить сообщение от веб-клиента менеджеру в Telegram"""
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        message_text = data.get("message_text", "").strip()
        client_name = data.get("client_name")
        
        if not chat_id or not message_text:
            return {"success": False, "error": "chat_id и message_text обязательны"}
        
        # Импортируем сервис менеджеров
        from telegram_bot.services.manager_service import manager_service
        
        # Отправляем сообщение менеджеру через Telegram
        success = await manager_service.send_message_to_manager(
            chat_id=chat_id,
            message_text=message_text,
            client_name=client_name
        )
        
        if success:
            return {"success": True, "message": "Сообщение отправлено менеджеру"}
        else:
            return {"success": False, "error": "Не удалось отправить сообщение"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения: {e}")
        return {
            "success": False,
            "error": "Внутренняя ошибка сервера"
        }

async def check_if_transferred_to_manager(session_id: str):
    """Проверить, передан ли веб-чат менеджеру"""
    try:
        from telegram_bot.models.database import AsyncSessionLocal
        from telegram_bot.models.support_models import SupportChat
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        async with AsyncSessionLocal() as session:
            # Ищем активный чат поддержки с указанным web_session_id
            from sqlalchemy import text
            result = await session.execute(
                select(SupportChat)
                .options(selectinload(SupportChat.manager))
                .where(
                    text("chat_metadata ->> 'web_session_id' = :session_id"),
                    SupportChat.is_active == True
                ).params(session_id=session_id)
            )
            support_chat = result.scalar_one_or_none()
            return support_chat
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки передачи чата менеджеру: {e}")
        return None

@chat_router.get("/api/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: str, limit: int = 50):
    """Получить сообщения чата"""
    try:
        from telegram_bot.models.database import AsyncSessionLocal
        from telegram_bot.models.support_models import SupportChat, ChatMessage
        from sqlalchemy import select, desc
        from sqlalchemy.orm import selectinload
        
        async with AsyncSessionLocal() as session:
            # Находим чат с сообщениями
            result = await session.execute(
                select(SupportChat).options(
                    selectinload(SupportChat.messages)
                ).where(SupportChat.chat_id == chat_id)
            )
            support_chat = result.scalar_one_or_none()
            
            if not support_chat:
                return {"success": False, "error": "Чат не найден"}
            
            # Получаем последние сообщения
            messages_query = select(ChatMessage).where(
                ChatMessage.chat_id == support_chat.id
            ).order_by(desc(ChatMessage.created_at)).limit(limit)
            
            messages_result = await session.execute(messages_query)
            messages = messages_result.scalars().all()
            
            # Форматируем сообщения
            formatted_messages = []
            for msg in reversed(messages):  # Показываем в хронологическом порядке
                formatted_messages.append({
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "sender_name": msg.sender_name,
                    "message": msg.message_text,
                    "timestamp": msg.created_at.isoformat(),
                    "is_read": msg.is_read
                })
            
            return {
                "success": True,
                "messages": formatted_messages,
                "chat_info": {
                    "chat_id": support_chat.chat_id,
                    "is_active": support_chat.is_active,
                    "client_name": support_chat.client_name,
                    "manager_id": support_chat.manager_id
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения сообщений: {e}")
        return {
            "success": False,
            "error": "Внутренняя ошибка сервера"
        }

# Обработка завершения работы
@chat_router.on_event("shutdown")
async def shutdown_event():
    """Завершение работы сервисов"""
    print("🔄 Завершение работы чат-сервиса...")
    if openrouter_ai:
        await openrouter_ai.close()
    await chat_manager.cleanup_sessions() # Убедитесь, что эта функция корректно останавливает задачу
    print("✅ Чат-сервис корректно завершен") 