"""
Сервис для управления менеджерами поддержки
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.orm import selectinload
from datetime import timezone

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
    
    async def get_available_manager(self) -> Optional[Manager]:
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
                # if exclude_ids: # This line was removed from the new_code, so it's removed here.
                #     query = query.where(~Manager.telegram_id.in_(exclude_ids))
                
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
                if not application or application.assigned_manager_id is not None:
                    logger.warning(f"Попытка назначить уже назначенную или несуществующую заявку #{application_id}")
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
                application.assigned_at = datetime.utcnow() # Устанавливаем время назначения
                
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
        limit: int = 10,
        offset: int = 0,
        show_all: bool = False
    ) -> List[Application]:
        """Получить заявки менеджера
        
        Args:
            telegram_id: Telegram ID менеджера
            status: Статус заявок для фильтрации
            limit: Максимальное количество заявок
            offset: Смещение для пагинации
            show_all: Показать все заявки (как для админа)
        """
        async with AsyncSessionLocal() as session:
            try:
                # Получаем менеджера
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return []
                
                # Если запрашиваются новые заявки
                if status == ApplicationStatus.NEW:
                    # Показываем неназначенные NEW заявки + незавершенные заявки этого менеджера
                    query = select(Application).where(
                        or_(
                            # Неназначенные новые заявки
                            and_(
                                Application.status == ApplicationStatus.NEW,
                                Application.assigned_manager_id.is_(None)
                            ),
                            # Незавершенные заявки этого менеджера
                            and_(
                                Application.assigned_manager_id == manager.id,
                                Application.status.in_([
                                    ApplicationStatus.ASSIGNED, 
                                    ApplicationStatus.IN_PROGRESS
                                ])
                            )
                        )
                    ).options(selectinload(Application.assigned_manager))
                # Если запрашиваются заявки в работе
                elif status == ApplicationStatus.IN_PROGRESS:
                    query = select(Application).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status.in_([
                                ApplicationStatus.ASSIGNED,
                                ApplicationStatus.IN_PROGRESS
                            ])
                        )
                    ).options(selectinload(Application.assigned_manager))
                # Если запрашиваются все заявки (для админа)
                elif show_all:
                    query = select(Application).where(
                        Application.status != ApplicationStatus.COMPLETED
                    ).options(
                        selectinload(Application.assigned_manager)
                    )
                # Если status is None (мои заявки) - исключаем завершенные
                elif status is None:
                    query = select(Application).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status != ApplicationStatus.COMPLETED
                        )
                    ).options(selectinload(Application.assigned_manager))
                # Все остальные конкретные статусы (включая COMPLETED)
                else:
                    query = select(Application).where(
                        Application.status == status
                    ).options(selectinload(Application.assigned_manager))

                    # Админ может видеть все заявки с этим статусом,
                    # обычный менеджер - только свои.
                    if not manager.is_admin:
                         query = query.where(Application.assigned_manager_id == manager.id)

                # Добавляем сортировку и пагинацию
                query = query.order_by(desc(Application.created_at)).limit(limit).offset(offset)

                result = await session.execute(query)
                return result.scalars().all()
            except Exception as e:
                logger.error(f"❌ Ошибка получения заявок менеджера: {e}")
                return []
    
    async def get_all_applications(self, limit: int = 20, offset: int = 0) -> tuple[List[Application], int]:
        """Получить все заявки в системе (для админов и менеджеров)
        
        Args:
            limit: Максимальное количество заявок
            offset: Смещение для пагинации
            
        Returns:
            Tuple[List[Application], int]: Список заявок и общее количество заявок
        """
        async with AsyncSessionLocal() as session:
            try:
                # Получаем общее количество заявок для пагинации
                total_count_query = select(func.count(Application.id))
                total_count_result = await session.execute(total_count_query)
                total_count = total_count_result.scalar() or 0
                
                # Запрос с пагинацией
                query = select(Application).order_by(desc(Application.created_at))
                
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                
                result = await session.execute(query)
                applications = result.scalars().all()
                
                return applications, total_count
            except Exception as e:
                logger.error(f"❌ Ошибка получения всех заявок: {e}")
                return [], 0

    async def get_available_new_applications(self, limit: int = 10) -> List[Application]:
        """Получить доступные новые заявки (неназначенные)"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(Application).where(
                    Application.status == ApplicationStatus.NEW,
                    Application.assigned_manager_id.is_(None)
                ).order_by(desc(Application.created_at)).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения новых заявок: {e}")
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
                today_utc = datetime.utcnow().date()
                today_applications_query = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status == ApplicationStatus.COMPLETED,
                            func.date(Application.processed_at) == today_utc
                        )
                    )
                )
                today_count = today_applications_query.scalar() or 0
                
                # Подсчет времени работы по заявкам за неделю
                week_ago_utc = datetime.utcnow() - timedelta(days=7)
                completed_apps_week_query = await session.execute(
                    select(Application).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status == ApplicationStatus.COMPLETED,
                            Application.processed_at >= week_ago_utc,
                            Application.assigned_at.isnot(None)
                        )
                    )
                )
                completed_apps_week = completed_apps_week_query.scalars().all()
                
                total_work_seconds = 0
                for app in completed_apps_week:
                    duration = app.processed_at - app.assigned_at
                    total_work_seconds += duration.total_seconds()
                
                week_work_hours = round(total_work_seconds / 3600, 1)

                # Конвертация времени последней активности в MSK
                last_seen_msk = "Никогда"
                if manager.last_seen:
                    # Устанавливаем таймзону UTC и конвертируем в MSK (UTC+3)
                    last_seen_msk_dt = manager.last_seen.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=3)))
                    last_seen_msk = last_seen_msk_dt.strftime('%Y-%m-%d %H:%M:%S')

                return {
                    "manager_name": f"{manager.first_name} {manager.last_name or ''}".strip(),
                    "status": manager.status.value,
                    "active_chats": len(active_chats),
                    "max_chats": manager.max_active_chats,
                    "total_applications": manager.total_applications,
                    "today_applications": today_count,
                    "avg_response_time": manager.avg_response_time,
                    "week_work_hours": week_work_hours,
                    "last_seen": last_seen_msk
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
    ) -> Optional[Dict[str, Any]]:
        """Создать чат поддержки из веб-чата"""
        async with AsyncSessionLocal() as session:
            try:
                # Находим доступного менеджера с детальным логированием
                logger.info(f"🔍 Начинаем поиск доступного менеджера для веб-чата")
                available_manager = await self.get_available_manager_for_chat()
                if not available_manager:
                    logger.warning("⚠️ Нет доступных менеджеров для переключения")
                    
                    # Дополнительная диагностика
                    all_managers = await session.execute(
                        select(Manager).where(Manager.is_active == True)
                    )
                    all_managers_list = all_managers.scalars().all()
                    
                    logger.info(f"📊 Всего активных менеджеров: {len(all_managers_list)}")
                    for mgr in all_managers_list:
                        logger.info(f"📊 Менеджер {mgr.first_name} (ID: {mgr.telegram_id}) - статус: {mgr.status.value}")
                        
                        # Проверяем активные чаты через Redis
                        redis_chats = await redis_service.get_manager_active_chats(str(mgr.telegram_id))
                        logger.info(f"📊 Redis чаты для {mgr.first_name}: {len(redis_chats)} (макс: {mgr.max_active_chats})")
                        
                        # Проверяем активные чаты через БД
                        db_chats = [chat for chat in mgr.support_chats if chat.is_active]
                        logger.info(f"📊 БД чаты для {mgr.first_name}: {len(db_chats)}")
                    
                    return None
                else:
                    logger.info(f"✅ Найден доступный менеджер: {available_manager.first_name}")
                
                # Подготавливаем метаданные с историей чата
                chat_metadata = {
                    "web_session_id": session_id, 
                    "source": "web_chat",
                    "chat_history": chat_history,
                    "created_by": "ai_transfer",
                    "transfer_timestamp": datetime.utcnow().isoformat()
                }
                
                # Создаем новый чат поддержки
                support_chat = SupportChat(
                    chat_id=f"web_{session_id}_{int(datetime.utcnow().timestamp())}",
                    chat_type=ChatType.TRANSFER_FROM_AI,
                    client_name=client_name,
                    client_phone=client_phone,
                    manager_id=available_manager.id,
                    is_active=True,
                    is_ai_handed_over=True,
                    created_at=datetime.utcnow(),
                    last_message_at=datetime.utcnow(),
                    chat_metadata=chat_metadata
                )
                
                session.add(support_chat)
                await session.flush()  # Получаем ID
                
                # Сохраняем историю чата как сообщения в БД (для удобства поиска)
                if chat_history:
                    for i, msg in enumerate(chat_history):
                        chat_message = ChatMessage(
                            chat_id=support_chat.id,
                            sender_type="ai_history" if msg.get("role") == "assistant" else "client_history",
                            sender_name=client_name if msg.get("role") == "user" else "ИИ-Консультант",
                            message_text=msg.get("content", ""),
                            message_type="text",
                            created_at=datetime.utcnow() - timedelta(minutes=len(chat_history) - i)  # Искусственно раздвигаем время
                        )
                        session.add(chat_message)
                
                await session.commit()
                
                # Возвращаем данные чата и менеджера
                chat_data = {
                    "id": support_chat.id,
                    "chat_id": support_chat.chat_id,
                    "client_name": support_chat.client_name,
                    "client_phone": support_chat.client_phone,
                    "manager_id": available_manager.id,
                    "manager_telegram_id": available_manager.telegram_id,
                    "manager_name": available_manager.first_name,
                    "is_active": support_chat.is_active,
                    "created_at": support_chat.created_at
                }
                
                logger.info(f"✅ Создан чат поддержки {support_chat.chat_id} для сессии {session_id}")
                return chat_data
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка создания чата поддержки: {e}")
                import traceback
                logger.error(f"Полная ошибка: {traceback.format_exc()}")
                return None
    
    async def get_available_manager_for_chat(self) -> Optional[Manager]:
        """Найти доступного менеджера для нового чата (используем Redis для корректного подсчета)"""
        async with AsyncSessionLocal() as session:
            try:
                # Ищем онлайн менеджеров с наименьшей загрузкой
                query = select(Manager).where(
                    and_(
                        Manager.is_active == True,
                        Manager.status == ManagerStatus.ONLINE
                    )
                )
                
                result = await session.execute(query)
                managers = result.scalars().all()
                
                if not managers:
                    logger.info("❌ Нет онлайн менеджеров")
                    return None
                
                # Находим менеджера с наименьшим количеством активных чатов (используем Redis)
                best_manager = None
                min_chats = float('inf')
                
                for manager in managers:
                    # Используем Redis для актуального подсчета активных чатов
                    active_chats = await redis_service.get_manager_active_chats(str(manager.telegram_id))
                    active_count = len(active_chats)
                    
                    logger.info(f"🔍 Менеджер {manager.first_name}: {active_count}/{manager.max_active_chats} чатов")
                    
                    # Проверяем лимит активных чатов
                    if active_count < manager.max_active_chats and active_count < min_chats:
                        min_chats = active_count
                        best_manager = manager
                        logger.info(f"✅ Потенциальный кандидат: {manager.first_name} с {active_count} чатами")
                
                if best_manager:
                    logger.info(f"🎯 Выбран менеджер: {best_manager.first_name} с {min_chats} активными чатами")
                else:
                    logger.warning("❌ Все менеджеры заняты (достигнут лимит чатов)")
                
                return best_manager
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска доступного менеджера: {e}")
                import traceback
                logger.error(f"Полная ошибка: {traceback.format_exc()}")
                return None
    
    async def notify_manager_new_chat_by_data(self, manager_telegram_id: int, chat_data: Dict[str, Any], chat_history: List[Dict[str, Any]] = None):
        """Уведомить менеджера о новом чате (используя данные чата)"""
        try:
            from aiogram import Bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from aiogram.enums import ParseMode
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            # Подготавливаем историю чата
            history_text = ""
            if chat_history:
                history_text = "\n\n💬 **История переписки с ИИ:**\n"
                for msg in chat_history[-3:]:  # Последние 3 сообщения
                    role_emoji = "👤" if msg.get("role") == "user" else "🤖"
                    content = msg.get("content", "")[:100] + ("..." if len(msg.get("content", "")) > 100 else "")
                    history_text += f"{role_emoji} {content}\n"
            
            text = f"""
🆕 **НОВЫЙ ЧАТ ОТ ВЕБ-КЛИЕНТА**

👤 **Клиент:** {chat_data.get('client_name') or 'Не указано'}
📞 **Телефон:** {chat_data.get('client_phone') or 'Не указано'}
💬 **ID чата:** `{chat_data['chat_id']}`
🕐 **Время:** {chat_data['created_at'].strftime('%d.%m.%Y %H:%M')}

ℹ️ Клиент был переключен с ИИ-консультанта на живого менеджера.{history_text}

**Используйте кнопки ниже для работы с чатом:**
            """
            
            # Создаем клавиатуру без кнопки "Позвонить" так как Telegram не поддерживает tel: схему
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text="✅ Принять чат", 
                        callback_data=f"accept_chat_{chat_data['id']}"
                    ),
                    InlineKeyboardButton(
                        text="📋 Подробности", 
                        callback_data=f"chat_details_{chat_data['id']}"
                    )
                ]
            ]
            
            # Добавляем кнопку "Активные чаты"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="💬 Активные чаты", 
                    callback_data="active_chats"
                )
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await bot.send_message(
                chat_id=manager_telegram_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Добавляем чат в активные чаты менеджера в Redis
            await redis_service.add_manager_active_chat(
                str(manager_telegram_id), 
                chat_data['chat_id']
            )
            
            logger.info(f"✅ Менеджер {manager_telegram_id} уведомлен о новом чате {chat_data['chat_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления менеджеру: {e}")
            import traceback
            logger.error(f"Полная ошибка: {traceback.format_exc()}")

    async def send_message_to_manager(
        self, 
        chat_id: str, 
        message_text: str, 
        client_name: str = None
    ) -> bool:
        """Отправить сообщение от веб-клиента менеджеру в Telegram"""
        try:
            from aiogram import Bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Находим чат поддержки
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(SupportChat)
                    .options(selectinload(SupportChat.manager))
                    .where(SupportChat.chat_id == chat_id)
                )
                support_chat = result.scalar_one_or_none()
                
                if not support_chat or not support_chat.manager:
                    logger.error(f"❌ Чат {chat_id} не найден или не назначен менеджер")
                    return False
                
                if not support_chat.is_active:
                    logger.error(f"❌ Чат {chat_id} неактивен")
                    return False
                
                bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
                
                # Обрезаем длинное сообщение
                display_message = message_text
                if len(message_text) > 1000:
                    display_message = message_text[:1000] + "...\n\n[Сообщение сокращено]"
                
                text = f"""
💬 **СООБЩЕНИЕ ИЗ ВЕБ-ЧАТА**

👤 **От:** {client_name or support_chat.client_name or 'Клиент'}
💬 **Чат:** `{chat_id}`

**Сообщение:**
{display_message}
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💬 Ответить", 
                            callback_data=f"reply_chat_{support_chat.id}"
                        ),
                        InlineKeyboardButton(
                            text="📋 Подробности чата", 
                            callback_data=f"chat_details_{support_chat.id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔚 Завершить чат", 
                            callback_data=f"close_chat_{support_chat.id}"
                        )
                    ]
                ])
                
                await bot.send_message(
                    chat_id=support_chat.manager.telegram_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                # Сохраняем сообщение в БД
                from telegram_bot.models.support_models import ChatMessage
                new_message = ChatMessage(
                    chat_id=support_chat.id,
                    sender_type="client",
                    sender_name=client_name or support_chat.client_name,
                    message_text=message_text,
                    message_type="text",
                    created_at=datetime.utcnow()
                )
                
                session.add(new_message)
                
                # Обновляем время последнего сообщения
                support_chat.last_message_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"✅ Сообщение от веб-клиента переслано менеджеру {support_chat.manager.telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения менеджеру: {e}")
            import traceback
            logger.error(f"Полная ошибка: {traceback.format_exc()}")
            return False
    
    async def get_manager_detailed_stats(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить детальную статистику менеджера"""
        async with AsyncSessionLocal() as session:
            try:
                manager = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                manager = manager.scalar_one_or_none()
                if not manager:
                    return None
                
                # Общая статистика
                total_apps = await session.execute(
                    select(func.count(Application.id)).where(
                        Application.assigned_manager_id == manager.id
                    )
                )
                total_applications = total_apps.scalar() or 0
                
                # Завершенные заявки
                completed_apps = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status == ApplicationStatus.COMPLETED
                        )
                    )
                )
                completed_applications = completed_apps.scalar() or 0
                
                # Отмененные заявки
                cancelled_apps = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.status == ApplicationStatus.CANCELLED
                        )
                    )
                )
                cancelled_applications = cancelled_apps.scalar() or 0
                
                # За месяц
                month_ago = datetime.utcnow() - timedelta(days=30)
                month_apps = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_manager_id == manager.id,
                            Application.processed_at >= month_ago
                        )
                    )
                )
                month_applications = month_apps.scalar() or 0
                
                # Часы работы за месяц
                month_sessions = await session.execute(
                    select(ManagerWorkSession).where(
                        and_(
                            ManagerWorkSession.manager_id == manager.id,
                            ManagerWorkSession.started_at >= month_ago
                        )
                    )
                )
                month_sessions = month_sessions.scalars().all()
                
                month_work_time = 0
                for session_obj in month_sessions:
                    if session_obj.ended_at:
                        work_time = (session_obj.ended_at - session_obj.started_at).total_seconds()
                        month_work_time += work_time
                
                # Процент успеха
                success_rate = round((completed_applications / max(total_applications, 1)) * 100, 1)
                
                # Рейтинг среди менеджеров
                all_managers = await session.execute(
                    select(Manager).where(Manager.is_active == True)
                    .order_by(desc(Manager.total_applications))
                )
                all_managers = all_managers.scalars().all()
                
                rank = 1
                for i, mgr in enumerate(all_managers, 1):
                    if mgr.id == manager.id:
                        rank = i
                        break
                
                return {
                    "manager_name": f"{manager.first_name} {manager.last_name or ''}".strip(),
                    "total_applications": total_applications,
                    "completed_applications": completed_applications,
                    "cancelled_applications": cancelled_applications,
                    "success_rate": success_rate,
                    "month_applications": month_applications,
                    "month_work_hours": round(month_work_time / 3600, 1),
                    "avg_response_time": manager.avg_response_time,
                    "rank": rank,
                    "total_managers": len(all_managers),
                    "client_rating": 4.5  # Пока захардкодим, потом можно добавить систему оценок
                }
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения детальной статистики: {e}")
                return None
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Получить общую статистику системы для админов"""
        async with AsyncSessionLocal() as session:
            try:
                # Общее количество менеджеров
                total_managers = await session.execute(
                    select(func.count(Manager.id)).where(Manager.is_active == True)
                )
                total_managers = total_managers.scalar() or 0
                
                # Менеджеры онлайн
                online_managers = await session.execute(
                    select(func.count(Manager.id)).where(
                        and_(
                            Manager.is_active == True,
                            Manager.status.in_([ManagerStatus.ONLINE, ManagerStatus.BUSY])
                        )
                    )
                )
                online_managers = online_managers.scalar() or 0
                
                # Активные чаты (из Redis или подсчет через базу)
                active_chats = 0  # Можно подсчитать через Redis
                
                # Заявки за сегодня
                today = datetime.utcnow().date()
                today_applications = await session.execute(
                    select(func.count(Application.id)).where(
                        func.date(Application.created_at) == today
                    )
                )
                today_applications = today_applications.scalar() or 0
                
                # За последний час
                hour_ago = datetime.utcnow() - timedelta(hours=1)
                hour_applications = await session.execute(
                    select(func.count(Application.id)).where(
                        Application.created_at >= hour_ago
                    )
                )
                hour_applications = hour_applications.scalar() or 0
                
                hour_completed = await session.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.processed_at >= hour_ago,
                            Application.status == ApplicationStatus.COMPLETED
                        )
                    )
                )
                hour_completed = hour_completed.scalar() or 0
                
                return {
                    "total_managers": total_managers,
                    "online_managers": online_managers,
                    "active_chats": active_chats,
                    "today_applications": today_applications,
                    "hour_applications": hour_applications,
                    "hour_completed": hour_completed
                }
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения системной статистики: {e}")
                return {
                    "total_managers": 0,
                    "online_managers": 0,
                    "active_chats": 0,
                    "today_applications": 0,
                    "hour_applications": 0,
                    "hour_completed": 0
                }

# Создаем глобальный экземпляр сервиса
manager_service = ManagerService() 