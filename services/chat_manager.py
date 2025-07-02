"""
Chat Manager - Управление сессиями чата
Хранение истории разговоров и управление контекстом
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, asdict
import aiofiles

@dataclass
class ChatMessage:
    """Структура сообщения в чате"""
    role: str  # "user" или "assistant"
    content: str
    timestamp: str
    message_id: str = None
    intent: str = None
    processing_time: float = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class ChatSession:
    """Структура сессии чата"""
    session_id: str
    user_id: str = None
    created_at: str = None
    last_activity: str = None
    messages: List[ChatMessage] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_activity is None:
            self.last_activity = self.created_at
        if self.messages is None:
            self.messages = []
        if self.context is None:
            self.context = {}

class ChatManager:
    """Менеджер чат-сессий"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.cleanup_interval = 3600  # Очистка каждый час
        self.session_timeout = 86400  # Сессия живет 24 часа
        self._cleanup_task = None  # Задача очистки сессий
    
    async def initialize(self):
        """Инициализация менеджера (запуск задачи очистки)"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self.cleanup_sessions())
            print("🧹 Запущена задача очистки устаревших сессий")
    
    async def create_session(self, user_id: str = None) -> str:
        """Создать новую сессию чата"""
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id or f"anonymous_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        self.sessions[session_id] = session
        
        print(f"🆕 Создана новая чат-сессия: {session_id} для пользователя {session.user_id}")
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Получить сессию по ID"""
        session = self.sessions.get(session_id)
        
        if session:
            # Обновляем время последней активности
            session.last_activity = datetime.now().isoformat()
        
        return session
    
    async def add_message(self, session_id: str, role: str, content: str, **kwargs) -> bool:
        """Добавить сообщение в сессию"""
        session = await self.get_session(session_id)
        
        if not session:
            print(f"❌ Сессия {session_id} не найдена")
            return False
        
        # Убираем timestamp из kwargs если он есть, чтобы избежать дублирования
        timestamp = kwargs.pop('timestamp', datetime.now().isoformat())
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=timestamp,
            **kwargs
        )
        
        session.messages.append(message)
        session.last_activity = datetime.now().isoformat()
        
        print(f"💬 Добавлено сообщение в сессию {session_id}: {role} - {len(content)} символов")
        
        return True
    
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Получить историю разговора для сессии"""
        session = await self.get_session(session_id)
        
        if not session:
            return []
        
        # Возвращаем последние сообщения в формате для OpenRouter
        history = []
        for message in session.messages[-limit:]:
            history.append({
                "role": message.role,
                "content": message.content
            })
        
        return history
    
    async def update_context(self, session_id: str, context_update: Dict[str, Any]) -> bool:
        """Обновить контекст сессии"""
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        session.context.update(context_update)
        session.last_activity = datetime.now().isoformat()
        
        return True
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Получить статистику сессии"""
        session = await self.get_session(session_id)
        
        if not session:
            return {}
        
        user_messages = [msg for msg in session.messages if msg.role == "user"]
        ai_messages = [msg for msg in session.messages if msg.role == "assistant"]
        
        stats = {
            "session_id": session_id,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "total_messages": len(session.messages),
            "user_messages": len(user_messages),
            "ai_messages": len(ai_messages),
            "average_response_time": self._calculate_avg_response_time(ai_messages),
            "session_duration": self._calculate_session_duration(session),
            "context": session.context
        }
        
        return stats
    
    def _calculate_avg_response_time(self, ai_messages: List[ChatMessage]) -> float:
        """Вычислить среднее время ответа ИИ"""
        times = [msg.processing_time for msg in ai_messages if msg.processing_time]
        
        if not times:
            return 0.0
        
        return sum(times) / len(times)
    
    def _calculate_session_duration(self, session: ChatSession) -> float:
        """Вычислить продолжительность сессии в минутах"""
        created = datetime.fromisoformat(session.created_at)
        last_activity = datetime.fromisoformat(session.last_activity)
        
        duration = last_activity - created
        return duration.total_seconds() / 60
    
    async def cleanup_sessions(self):
        """Периодическая очистка устаревших сессий"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = datetime.now()
                sessions_to_remove = []
                
                for session_id, session in self.sessions.items():
                    last_activity = datetime.fromisoformat(session.last_activity)
                    age = (current_time - last_activity).total_seconds()
                    
                    if age > self.session_timeout:
                        sessions_to_remove.append(session_id)
                
                # Удаляем устаревшие сессии
                for session_id in sessions_to_remove:
                    del self.sessions[session_id]
                    print(f"🗑️ Удалена устаревшая сессия: {session_id}")
                
                if sessions_to_remove:
                    print(f"🧹 Очистка завершена. Удалено {len(sessions_to_remove)} сессий. Осталось: {len(self.sessions)}")
                
            except Exception as e:
                print(f"❌ Ошибка при очистке сессий: {e}")
    
    async def export_session(self, session_id: str, filepath: str = None) -> bool:
        """Экспорт сессии в JSON файл"""
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        if filepath is None:
            filepath = f"chat_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Конвертируем в словарь для JSON
            session_data = asdict(session)
            
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
            
            print(f"💾 Сессия {session_id} экспортирована в {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта сессии: {e}")
            return False
    
    async def get_all_sessions_stats(self) -> Dict[str, Any]:
        """Получить общую статистику по всем сессиям"""
        total_sessions = len(self.sessions)
        active_sessions = 0
        total_messages = 0
        
        current_time = datetime.now()
        
        for session in self.sessions.values():
            last_activity = datetime.fromisoformat(session.last_activity)
            if (current_time - last_activity).total_seconds() < 300:  # Активна если была активность в последние 5 минут
                active_sessions += 1
            
            total_messages += len(session.messages)
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
        }

    async def shutdown(self):
        """Корректное завершение работы менеджера"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            print("🛑 Задача очистки сессий остановлена")

# Создаем глобальный экземпляр
chat_manager = ChatManager() 