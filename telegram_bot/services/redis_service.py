"""
Сервис для работы с Redis
Кэширование и управление состояниями бота
"""
import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Dict, List
from telegram_bot.config.settings import settings

logger = logging.getLogger(__name__)

class RedisService:
    """Сервис для работы с Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
    
    async def connect(self):
        """Подключение к Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Проверяем соединение
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Успешное подключение к Redis")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("✅ Отключение от Redis")
    
    async def set_value(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранить значение в Redis"""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Сериализуем значение в JSON если это не строка
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            
            if ttl:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в Redis {key}: {e}")
            return False
    
    async def get_value(self, key: str) -> Optional[Any]:
        """Получить значение из Redis"""
        try:
            if not self.is_connected:
                await self.connect()
            
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            # Пытаемся десериализовать JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения из Redis {key}: {e}")
            return None
    
    async def delete_key(self, key: str) -> bool:
        """Удалить ключ из Redis"""
        try:
            if not self.is_connected:
                await self.connect()
            
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из Redis {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Проверить существование ключа"""
        try:
            if not self.is_connected:
                await self.connect()
            
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ Ошибка проверки ключа Redis {key}: {e}")
            return False
    
    async def get_keys_pattern(self, pattern: str) -> List[str]:
        """Получить ключи по паттерну"""
        try:
            if not self.is_connected:
                await self.connect()
            
            return await self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"❌ Ошибка поиска ключей Redis {pattern}: {e}")
            return []
    
    # Специальные методы для состояний бота
    
    async def set_manager_status(self, telegram_id: str, status: str, ttl: int = 3600) -> bool:
        """Установить статус менеджера"""
        key = f"manager_status:{telegram_id}"
        return await self.set_value(key, status, ttl)
    
    async def get_manager_status(self, telegram_id: str) -> Optional[str]:
        """Получить статус менеджера"""
        key = f"manager_status:{telegram_id}"
        return await self.get_value(key)
    
    async def set_chat_assignment(self, chat_id: str, manager_telegram_id: str, ttl: int = 7200) -> bool:
        """Назначить чат менеджеру"""
        key = f"chat_assignment:{chat_id}"
        return await self.set_value(key, manager_telegram_id, ttl)
    
    async def get_chat_assignment(self, chat_id: str) -> Optional[str]:
        """Получить назначенного менеджера для чата"""
        key = f"chat_assignment:{chat_id}"
        return await self.get_value(key)
    
    async def set_manager_active_chats(self, telegram_id: str, chat_ids: List[str], ttl: int = 3600) -> bool:
        """Установить активные чаты менеджера"""
        key = f"manager_active_chats:{telegram_id}"
        return await self.set_value(key, chat_ids, ttl)
    
    async def get_manager_active_chats(self, telegram_id: str) -> List[str]:
        """Получить активные чаты менеджера"""
        key = f"manager_active_chats:{telegram_id}"
        result = await self.get_value(key)
        return result if result else []
    
    async def add_manager_active_chat(self, telegram_id: str, chat_id: str) -> bool:
        """Добавить активный чат менеджеру"""
        active_chats = await self.get_manager_active_chats(telegram_id)
        if chat_id not in active_chats:
            active_chats.append(chat_id)
            return await self.set_manager_active_chats(telegram_id, active_chats)
        return True
    
    async def remove_manager_active_chat(self, telegram_id: str, chat_id: str) -> bool:
        """Удалить активный чат у менеджера"""
        active_chats = await self.get_manager_active_chats(telegram_id)
        if chat_id in active_chats:
            active_chats.remove(chat_id)
            return await self.set_manager_active_chats(telegram_id, active_chats)
        return True
    
    async def set_web_chat_session(self, session_id: str, data: Dict, ttl: int = 7200) -> bool:
        """Сохранить данные веб-чата"""
        key = f"web_chat:{session_id}"
        return await self.set_value(key, data, ttl)
    
    async def get_web_chat_session(self, session_id: str) -> Optional[Dict]:
        """Получить данные веб-чата"""
        key = f"web_chat:{session_id}"
        return await self.get_value(key)
    
    async def set_notification_queue(self, notification_id: str, data: Dict, ttl: int = 600) -> bool:
        """Добавить уведомление в очередь"""
        key = f"notification:{notification_id}"
        return await self.set_value(key, data, ttl)
    
    async def get_pending_notifications(self) -> List[Dict]:
        """Получить все ожидающие уведомления"""
        keys = await self.get_keys_pattern("notification:*")
        notifications = []
        
        for key in keys:
            data = await self.get_value(key)
            if data:
                notifications.append(data)
        
        return notifications

# Создаем глобальный экземпляр сервиса
redis_service = RedisService() 