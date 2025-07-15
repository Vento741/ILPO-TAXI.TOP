"""
Сервис для работы с заявками и интеграции с API сайта
"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_bot.models.database import AsyncSessionLocal
from telegram_bot.models.support_models import Application, ApplicationStatus
from telegram_bot.services.manager_service import manager_service
from telegram_bot.config.settings import settings

logger = logging.getLogger(__name__)

class ApplicationService:
    """Сервис для работы с заявками"""
    
    def __init__(self):
        self.api_url = settings.FASTAPI_URL
        self.api_secret = settings.API_SECRET_KEY
    
    async def create_application_from_api(self, application_data: Dict) -> Optional[Application]:
        """Создать заявку из данных API сайта"""
        async with AsyncSessionLocal() as session:
            try:
                # Создаем новую заявку
                new_application = Application(
                    full_name=application_data.get("fullName", ""),
                    phone=application_data.get("phone", ""),
                    age=application_data.get("age"),
                    city=application_data.get("city", ""),
                    category=application_data.get("category", ""),
                    experience=application_data.get("experience"),
                    transport=application_data.get("transport"),
                    load_capacity=application_data.get("loadCapacity"),
                    additional_info=application_data.get("additionalInfo"),
                    status=ApplicationStatus.NEW
                )
                
                session.add(new_application)
                await session.commit()
                await session.refresh(new_application)
                
                logger.info(f"✅ Создана новая заявка #{new_application.id} от {new_application.full_name}")
                
                # Автоматически назначаем менеджера если включено
                if settings.AUTO_ASSIGN_MANAGERS:
                    await self.auto_assign_application(new_application.id)
                
                return new_application
                
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка создания заявки: {e}")
                return None
    
    async def auto_assign_application(self, application_id: int) -> bool:
        """Автоматически назначить заявку доступному менеджеру"""
        try:
            # Ищем доступного менеджера
            available_manager = await manager_service.get_available_manager()
            
            if not available_manager:
                logger.info(f"Нет доступных менеджеров для заявки #{application_id}")
                return False
            
            # Назначаем заявку
            success = await manager_service.assign_application_to_manager(
                application_id, 
                available_manager.telegram_id
            )
            
            if success:
                logger.info(f"✅ Заявка #{application_id} автоматически назначена менеджеру {available_manager.first_name}")
                
                # Уведомляем менеджера
                await self.notify_manager_about_new_application(available_manager.telegram_id, application_id)
                return True
            else:
                logger.error(f"❌ Не удалось назначить заявку #{application_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка автоназначения заявки: {e}")
            return False
    
    async def notify_manager_about_new_application(self, manager_telegram_id: int, application_id: int):
        """Уведомить менеджера о новой заявке через Telegram"""
        try:
            from aiogram import Bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            # Получаем заявку
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, application_id)
                
                if not application:
                    return
                
                # Формируем сообщение
                text = f"""
🔔 **Новая заявка назначена вам!**

📋 **Заявка #{application.id}**
👤 **Имя:** {application.full_name}
📱 **Телефон:** {application.phone}
🏙️ **Город:** {application.city}
🚗 **Категория:** {self.get_category_text(application.category)}

📅 **Время:** {application.created_at.strftime('%d.%m.%Y %H:%M')}

Нажмите кнопку ниже для обработки заявки.
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Открыть заявку", callback_data=f"app_details_{application.id}")],
                    [InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{application.id}")],
                    [InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{application.phone}")]
                ])
                
                await bot.send_message(
                    chat_id=manager_telegram_id,
                    text=text,
                    reply_markup=keyboard
                )
                
                logger.info(f"✅ Менеджер {manager_telegram_id} уведомлен о заявке #{application_id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления менеджера: {e}")
    
    async def get_pending_applications(self, limit: int = 10) -> List[Application]:
        """Получить список новых заявок"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Application)
                    .where(Application.status == ApplicationStatus.NEW)
                    .order_by(Application.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(f"❌ Ошибка получения заявок: {e}")
                return []
    
    async def notify_admins_about_new_application(self, application: Application):
        """Уведомить админов о новой заявке"""
        if not settings.ADMIN_IDS:
            return
        
        try:
            from aiogram import Bot
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            text = f"""
📊 **Новая заявка в системе**

📋 **#ID{application.id}**
👤 {application.full_name}
📱 {application.phone}
🏙️ {application.city}
🚗 {self.get_category_text(application.category)}

⏰ {application.created_at.strftime('%d.%m.%Y %H:%M')}
            """
            
            for admin_id in settings.ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=text)
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления админов: {e}")
    
    def get_category_text(self, category: str) -> str:
        """Получить текстовое описание категории"""
        categories = {
            "driver": "🚗 Водитель",
            "courier": "📦 Курьер", 
            "both": "🚗📦 Водитель и курьер",
            "cargo": "🚛 Грузоперевозки"
        }
        return categories.get(category, category)
    
    async def check_for_new_applications(self):
        """Периодическая проверка новых заявок (если нужно)"""
        try:
            # Можно добавить логику для периодической проверки
            # или интеграции с внешним API
            pass
        except Exception as e:
            logger.error(f"❌ Ошибка проверки новых заявок: {e}")

# Создаем глобальный экземпляр сервиса
application_service = ApplicationService()

# Функция-хелпер для интеграции с API сайта
async def handle_new_application_from_site(application_data: Dict) -> bool:
    """Обработать новую заявку с сайта"""
    try:
        # Создаем заявку в базе данных
        application = await application_service.create_application_from_api(application_data)
        
        if application:
            # Уведомляем админов
            await application_service.notify_admins_about_new_application(application)
            
            logger.info(f"✅ Заявка с сайта успешно обработана: {application.full_name}")
            return True
        else:
            logger.error("❌ Не удалось создать заявку с сайта")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки заявки с сайта: {e}")
        return False 