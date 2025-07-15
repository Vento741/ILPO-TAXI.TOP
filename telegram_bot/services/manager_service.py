"""
Сервис для управления менеджерами поддержки
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from telegram_bot.models.database import AsyncSessionLocal
from telegram_bot.models.support_models import (
    Manager, ManagerStatus, Application, ApplicationStatus,
    SupportChat, ChatType, ManagerWorkSession, ChatMessage
)
from telegram_bot.services.redis_service import redis_service
from telegram_bot.config.settings import settings

logger = logging.getLogger(__name__)

class ManagerService:
    """Сервис для управления менеджерами"""
    
    async def register_manager(
        self, 
        telegram_id: int, 
        username: str, 
        first_name: str, 
        last_name: Optional[str] = None,
        is_admin: bool = False
    ) -> Manager:
        """Регистрация нового менеджера"""
        
        async with AsyncSessionLocal() as session:
            try:
                # Проверяем, существует ли уже такой менеджер
                existing_manager = await self.get_manager_by_telegram_id(telegram_id)
                if existing_manager:
                    # Обновляем информацию
                    existing_manager.username = username
                    existing_manager.first_name = first_name
                    existing_manager.last_name = last_name
                    existing_manager.is_active = True
                    existing_manager.last_seen = datetime.utcnow()
                    
                    await session.commit()
                    logger.info(f"✅ Обновлен менеджер: {first_name} (@{username})")
                    return existing_manager
                
                # Создаем нового менеджера
                new_manager = Manager(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_admin=is_admin,
                    status=ManagerStatus.OFFLINE,
                    is_active=True
                )
                
                session.add(new_manager)
                await session.commit()
                await session.refresh(new_manager)
                
                logger.info(f"✅ Зарегистрирован новый менеджер: {first_name} (@{username})")
                return new_manager
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка регистрации менеджера: {e}")
                raise
    
    async def get_manager_by_telegram_id(self, telegram_id: int) -> Optional[Manager]:
        """Получить менеджера по Telegram ID"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"❌ Ошибка получения менеджера {telegram_id}: {e}")
                return None
    
    async def get_active_managers(self) -> List[Manager]:
        """Получить список активных менеджеров"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Manager).where(
                        and_(
                            Manager.is_active == True,
                            Manager.status.in_([ManagerStatus.ONLINE, ManagerStatus.BUSY])
                        )
                    ).order_by(Manager.last_seen.desc())
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(f"❌ Ошибка получения активных менеджеров: {e}")
                return []
    
    async def set_manager_status(self, telegram_id: int, status: ManagerStatus) -> bool:
        """Установить статус менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                
                if not manager:
                    return False
                
                manager.status = status
                manager.last_seen = datetime.utcnow()
                
                # Обновляем статус в Redis
                await redis_service.set_manager_status(str(telegram_id), status.value)
                
                await session.commit()
                logger.info(f"✅ Статус менеджера {manager.first_name} изменен на {status.value}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка изменения статуса менеджера: {e}")
                return False
    
    async def get_available_manager(self, exclude_ids: List[str] = None) -> Optional[Manager]:
        """Найти доступного менеджера для назначения"""
        async with AsyncSessionLocal() as session:
            try:
                # Строим запрос для поиска доступных менеджеров
                query = select(Manager).where(
                    and_(
                        Manager.is_active == True,
                        Manager.status == ManagerStatus.ONLINE
                    )
                )
                
                # Исключаем определенных менеджеров если нужно
                if exclude_ids:
                    query = query.where(~Manager.telegram_id.in_(exclude_ids))
                
                result = await session.execute(query)
                managers = result.scalars().all()
                
                if not managers:
                    return None
                
                # Выбираем менеджера с наименьшим количеством активных чатов
                best_manager = None
                min_chats = float('inf')
                
                for manager in managers:
                    active_chats = await redis_service.get_manager_active_chats(str(manager.telegram_id))
                    active_count = len(active_chats)
                    
                    # Проверяем лимит активных чатов
                    if active_count < manager.max_active_chats and active_count < min_chats:
                        min_chats = active_count
                        best_manager = manager
                
                return best_manager
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска доступного менеджера: {e}")
                return None
    
    async def assign_application_to_manager(
        self, 
        application_id: int, 
        manager_telegram_id: int
    ) -> bool:
        """Назначить заявку менеджеру"""
        async with AsyncSessionLocal() as session:
            try:
                # Получаем заявку
                application = await session.get(Application, application_id)
                if not application:
                    return False
                
                # Получаем менеджера
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == manager_telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return False
                
                # Назначаем заявку
                application.assigned_manager_id = manager.id
                application.status = ApplicationStatus.ASSIGNED
                application.processed_at = datetime.utcnow()
                
                # Обновляем статистику менеджера
                manager.total_applications += 1
                
                await session.commit()
                
                logger.info(f"✅ Заявка #{application_id} назначена менеджеру {manager.first_name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка назначения заявки: {e}")
                return False
    
    async def get_manager_applications(
        self, 
        telegram_id: int, 
        status: Optional[ApplicationStatus] = None,
        limit: int = 10
    ) -> List[Application]:
        """Получить заявки менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                # Получаем менеджера
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return []
                
                # Строим запрос
                query = select(Application).where(Application.assigned_manager_id == manager.id)
                
                if status:
                    query = query.where(Application.status == status)
                
                query = query.order_by(desc(Application.created_at)).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения заявок менеджера: {e}")
                return []
    
    async def start_work_session(self, telegram_id: int) -> bool:
        """Начать рабочую сессию менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return False
                
                # Проверяем, нет ли уже активной сессии
                active_session = await session.execute(
                    select(ManagerWorkSession).where(
                        and_(
                            ManagerWorkSession.manager_id == manager.id,
                            ManagerWorkSession.ended_at.is_(None)
                        )
                    )
                )
                
                if active_session.scalar_one_or_none():
                    return True  # Сессия уже активна
                
                # Создаем новую сессию
                new_session = ManagerWorkSession(
                    manager_id=manager.id,
                    started_at=datetime.utcnow()
                )
                
                session.add(new_session)
                
                # Устанавливаем статус онлайн
                manager.status = ManagerStatus.ONLINE
                manager.last_seen = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"✅ Начата рабочая сессия для {manager.first_name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка начала рабочей сессии: {e}")
                return False
    
    async def end_work_session(self, telegram_id: int) -> bool:
        """Завершить рабочую сессию менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return False
                
                # Находим активную сессию
                active_session = await session.execute(
                    select(ManagerWorkSession).where(
                        and_(
                            ManagerWorkSession.manager_id == manager.id,
                            ManagerWorkSession.ended_at.is_(None)
                        )
                    )
                )
                active_session = active_session.scalar_one_or_none()
                
                if active_session:
                    active_session.ended_at = datetime.utcnow()
                
                # Устанавливаем статус офлайн
                manager.status = ManagerStatus.OFFLINE
                manager.last_seen = datetime.utcnow()
                
                # Очищаем активные чаты в Redis
                await redis_service.set_manager_active_chats(str(telegram_id), [])
                
                await session.commit()
                
                logger.info(f"✅ Завершена рабочая сессия для {manager.first_name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка завершения рабочей сессии: {e}")
                return False
    
    async def get_manager_stats(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return None
                
                # Активные чаты
                active_chats = await redis_service.get_manager_active_chats(str(telegram_id))
                
                # Заявки за сегодня
                today = datetime.utcnow().date()
                today_applications = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            func.date(Application.processed_at) == today
                        )
                    )
                )
                today_count = today_applications.scalar() or 0
                
                # Статистика сессий за неделю
                week_ago = datetime.utcnow() - timedelta(days=7)
                week_sessions = await session.execute(
                    select(ManagerWorkSession).where(
                        and_(
                            ManagerWorkSession.manager_id == manager.id,
                            ManagerWorkSession.started_at >= week_ago
                        )
                    )
                )
                week_sessions = week_sessions.scalars().all()
                
                total_work_time = 0
                for session_obj in week_sessions:
                    if session_obj.ended_at:
                        work_time = (session_obj.ended_at - session_obj.started_at).total_seconds()
                        total_work_time += work_time
                
                return {
                    "manager_name": f"{manager.first_name} {manager.last_name or ''}".strip(),
                    "status": manager.status.value,
                    "active_chats": len(active_chats),
                    "max_chats": manager.max_active_chats,
                    "total_applications": manager.total_applications,
                    "today_applications": today_count,
                    "avg_response_time": manager.avg_response_time,
                    "week_work_hours": round(total_work_time / 3600, 1),
                    "last_seen": manager.last_seen.isoformat() if manager.last_seen else None
                }
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения статистики менеджера: {e}")
                return None
    
    async def update_manager_response_time(self, telegram_id: int, response_time: int):
        """Обновить среднее время ответа менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return
                
                # Вычисляем новое среднее время (простое скользящее среднее)
                if manager.avg_response_time == 0:
                    manager.avg_response_time = response_time
                else:
                    # Используем весовой коэффициент для сглаживания
                    weight = 0.2  # 20% веса для нового значения
                    manager.avg_response_time = int(
                        manager.avg_response_time * (1 - weight) + response_time * weight
                    )
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка обновления времени ответа: {e}")
    
    async def create_support_chat(
        self, 
        session_id: str,
        chat_history: List[Dict[str, Any]],
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None
    ) -> Optional[SupportChat]:
        """Создать чат поддержки из веб-чата"""
        async with AsyncSessionLocal() as session:
            try:
                # Находим доступного менеджера
                available_manager = await self.get_available_manager()
                if not available_manager:
                    logger.warning("⚠️ Нет доступных менеджеров для переключения")
                    return None
                
                # Создаем новый чат поддержки
                support_chat = SupportChat(
                    chat_id=f"web_{session_id}_{datetime.utcnow().timestamp()}",
                    chat_type=ChatType.TRANSFER_FROM_AI,
                    client_name=client_name,
                    client_phone=client_phone,
                    manager_id=available_manager.id,
                    is_active=True,
                    is_ai_handed_over=True,
                    created_at=datetime.utcnow(),
                    last_message_at=datetime.utcnow(),
                    chat_metadata={"web_session_id": session_id, "source": "web_chat"}
                )
                
                session.add(support_chat)
                await session.flush()  # Получаем ID чата
                
                # Сохраняем историю чата как сообщения
                for i, message in enumerate(chat_history):
                    chat_message = ChatMessage(
                        chat_id=support_chat.id,
                        sender_type="client" if message.get("type") == "user" else "system",
                        sender_name=client_name or "Клиент",
                        message_text=message.get("content", ""),
                        message_type="text",
                        created_at=datetime.utcnow()
                    )
                    session.add(chat_message)
                
                # Обновляем статус менеджера
                available_manager.status = ManagerStatus.BUSY
                available_manager.last_seen = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"✅ Создан чат поддержки {support_chat.chat_id} для менеджера {available_manager.first_name}")
                return support_chat
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка создания чата поддержки: {e}")
                return None
    
    async def get_available_manager(self) -> Optional[Manager]:
        """Найти доступного менеджера для нового чата"""
        async with AsyncSessionLocal() as session:
            try:
                # Ищем онлайн менеджеров с наименьшей загрузкой
                query = select(Manager).where(
                    and_(
                        Manager.is_active == True,
                        Manager.status == ManagerStatus.ONLINE
                    )
                ).options(selectinload(Manager.support_chats))
                
                result = await session.execute(query)
                managers = result.scalars().all()
                
                if not managers:
                    return None
                
                # Находим менеджера с наименьшим количеством активных чатов
                best_manager = None
                min_chats = float('inf')
                
                for manager in managers:
                    active_chats_count = len([
                        chat for chat in manager.support_chats 
                        if chat.is_active
                    ])
                    
                    if (active_chats_count < manager.max_active_chats and 
                        active_chats_count < min_chats):
                        best_manager = manager
                        min_chats = active_chats_count
                
                return best_manager
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска доступного менеджера: {e}")
                return None
    
    async def notify_manager_new_chat(self, manager_telegram_id: int, chat: SupportChat):
        """Уведомить менеджера о новом чате (через Telegram)"""
        try:
            # Здесь будет интеграция с Telegram ботом для отправки уведомления
            # Пока просто логируем
            logger.info(f"📬 Уведомление менеджеру {manager_telegram_id} о новом чате {chat.chat_id}")
            
            # TODO: Реализовать отправку сообщения через Telegram бота
            # await telegram_bot.send_message(
            #     chat_id=manager_telegram_id,
            #     text=f"🆕 Новый чат от веб-клиента\n"
            #          f"👤 Клиент: {chat.client_name or 'Не указано'}\n"
            #          f"📞 Телефон: {chat.client_phone or 'Не указано'}\n"
            #          f"💬 ID чата: {chat.chat_id}"
            # )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления менеджеру: {e}")

# Создаем глобальный экземпляр сервиса
manager_service = ManagerService() 