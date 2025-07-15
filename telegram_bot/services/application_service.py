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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
                    additional_info=self._format_additional_info(application_data),
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
    
    def _format_additional_info(self, data: Dict) -> str:
        """Форматирование дополнительной информации из всех полей формы"""
        info_parts = []
        
        # Основная информация
        if data.get("citizenship"):
            citizenship_map = {
                "rf": "Гражданин РФ",
                "eaeu": "Гражданин ЕАЭС", 
                "other": "Гражданин другой страны"
            }
            info_parts.append(f"Гражданство: {citizenship_map.get(data['citizenship'], data['citizenship'])}")
        
        if data.get("workStatus"):
            status_map = {
                "self_employed": "Самозанятый",
                "park_self_employed": "Парковая самозанятость",
                "ip": "ИП (УСН 6%)",
                "employee": "Трудовой договор",
                "not_sure": "Не определился"
            }
            info_parts.append(f"Статус работы: {status_map.get(data['workStatus'], data['workStatus'])}")
        
        # Для водителей
        if data.get("hasDriverLicense"):
            license_map = {
                "yes": "Есть права категории B",
                "getting": "Получаю права",
                "no": "Нет прав"
            }
            info_parts.append(f"Водительские права: {license_map.get(data['hasDriverLicense'], data['hasDriverLicense'])}")
        
        if data.get("hasCar"):
            car_map = {
                "own": "Есть собственный автомобиль",
                "rent": "Планирую арендовать",
                "no": "Нет автомобиля"
            }
            info_parts.append(f"Автомобиль: {car_map.get(data['hasCar'], data['hasCar'])}")
        
        if data.get("carBrand") and data.get("carModel"):
            car_info = f"{data['carBrand']} {data['carModel']}"
            if data.get("carYear"):
                car_info += f" ({data['carYear']} г.)"
            info_parts.append(f"Автомобиль: {car_info}")
        
        if data.get("carClass"):
            class_map = {
                "economy": "Эконом",
                "comfort": "Комфорт",
                "comfort_plus": "Комфорт+",
                "business": "Бизнес"
            }
            info_parts.append(f"Желаемый класс: {class_map.get(data['carClass'], data['carClass'])}")
        
        if data.get("hasTaxiPermit"):
            permit_map = {
                "yes": "Есть разрешение на такси",
                "getting": "Оформляю разрешение",
                "no": "Нет разрешения",
                "help_needed": "Нужна помощь в получении"
            }
            info_parts.append(f"Разрешение такси: {permit_map.get(data['hasTaxiPermit'], data['hasTaxiPermit'])}")
        
        # Для курьеров
        if data.get("deliveryType") and isinstance(data["deliveryType"], list):
            delivery_map = {
                "yandex_food": "Яндекс.Еда",
                "yandex_delivery": "Яндекс.Доставка", 
                "yandex_lavka": "Яндекс.Лавка",
                "all": "Все категории"
            }
            delivery_types = [delivery_map.get(dt, dt) for dt in data["deliveryType"]]
            info_parts.append(f"Категории доставки: {', '.join(delivery_types)}")
        
        if data.get("hasThermoBag"):
            bag_map = {
                "yes": "Есть термосумка",
                "buying": "Планирую купить",
                "rent": "Буду арендовать",
                "no": "Нет термосумки"
            }
            info_parts.append(f"Термосумка: {bag_map.get(data['hasThermoBag'], data['hasThermoBag'])}")
        
        if data.get("courierLicense"):
            courier_license_map = {
                "yes": "Есть права категории B",
                "motorcycle": "Есть права категории A/A1",
                "no": "Нет прав"
            }
            info_parts.append(f"Права для курьера: {courier_license_map.get(data['courierLicense'], data['courierLicense'])}")
        
        # Для грузовых
        if data.get("truckType"):
            truck_map = {
                "tent": "Тентованный",
                "closed": "Закрытый",
                "refrigerator": "Рефрижератор",
                "platform": "Платформа",
                "dump": "Самосвал"
            }
            info_parts.append(f"Тип кузова: {truck_map.get(data['truckType'], data['truckType'])}")
        
        if data.get("cargoLicense"):
            cargo_license_map = {
                "b": "Категория B (до 3,5т)",
                "c": "Категория C",
                "ce": "Категория CE",
                "no": "Нет прав на грузовой"
            }
            info_parts.append(f"Права на грузовой: {cargo_license_map.get(data['cargoLicense'], data['cargoLicense'])}")
        
        # Опыт и документы
        if data.get("workExperience"):
            exp_map = {
                "no_experience": "Нет опыта",
                "less_year": "Менее года",
                "1_3_years": "1-3 года",
                "3_5_years": "3-5 лет",
                "more_5_years": "Более 5 лет"
            }
            info_parts.append(f"Опыт работы: {exp_map.get(data['workExperience'], data['workExperience'])}")
        
        if data.get("previousPlatforms"):
            info_parts.append(f"Работал в: {data['previousPlatforms']}")
        
        if data.get("hasMedicalCert"):
            med_map = {
                "yes": "Есть медсправка",
                "expired": "Справка просрочена",
                "no": "Нет справки",
                "help_needed": "Нужна помощь в получении"
            }
            info_parts.append(f"Медсправка: {med_map.get(data['hasMedicalCert'], data['hasMedicalCert'])}")
        
        if data.get("documents") and isinstance(data["documents"], list):
            doc_map = {
                "passport": "Паспорт",
                "driver_license": "Водительские права",
                "snils": "СНИЛС",
                "inn": "ИНН",
                "car_docs": "Документы на авто"
            }
            docs = [doc_map.get(doc, doc) for doc in data["documents"]]
            info_parts.append(f"Документы: {', '.join(docs)}")
        
        # Предпочтения
        if data.get("preferredTime"):
            time_map = {
                "9-12": "09:00-12:00",
                "12-15": "12:00-15:00", 
                "15-18": "15:00-18:00",
                "18-21": "18:00-21:00",
                "any": "Любое время"
            }
            info_parts.append(f"Удобное время звонка: {time_map.get(data['preferredTime'], data['preferredTime'])}")
        
        if data.get("workSchedule"):
            schedule_map = {
                "full_time": "Полный день",
                "part_time": "Неполный день",
                "weekends": "Только выходные",
                "evenings": "Вечерние часы",
                "flexible": "Гибкий график"
            }
            info_parts.append(f"График работы: {schedule_map.get(data['workSchedule'], data['workSchedule'])}")
        
        if data.get("email"):
            info_parts.append(f"Email: {data['email']}")
        
        if data.get("comments"):
            info_parts.append(f"Комментарии: {data['comments']}")
        
        # Согласия
        agreements = []
        if data.get("hasDocuments"):
            agreements.append("Подтвердил наличие документов")
        if data.get("agreeTerms"):
            agreements.append("Согласился с условиями")
        if data.get("agreeMarketing"):
            agreements.append("Согласился на рассылку")
        
        if agreements:
            info_parts.append(f"Согласия: {', '.join(agreements)}")
        
        if data.get("timestamp"):
            info_parts.append(f"Время подачи: {data['timestamp']}")
        
        return "\n".join(info_parts)
    
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
                
                # Формируем детальное сообщение
                text = f"""
🔔 **НОВАЯ ЗАЯВКА НАЗНАЧЕНА ВАМ!**

📋 **Заявка #{application.id}**
{self.get_category_text(application.category)}

👤 **Основная информация:**
• Имя: {application.full_name}
• Телефон: {application.phone}
• Возраст: {application.age if application.age else 'Не указан'} лет
• Город: {application.city}

🚗 **Профессиональная информация:**
"""
                
                # Добавляем специфичные поля в зависимости от категории
                if application.category in ['driver', 'both', 'cargo']:
                    if application.experience:
                        text += f"• Стаж вождения: {application.experience} лет\n"
                
                if application.category in ['courier', 'both']:
                    if application.transport:
                        transport_map = {
                            "foot": "🚶 Пеший курьер",
                            "bike": "🚴 Велосипед",
                            "scooter": "🛴 Электросамокат",
                            "motorcycle": "🏍️ Мотоцикл/скутер",
                            "car": "🚗 Автомобиль"
                        }
                        text += f"• Транспорт: {transport_map.get(application.transport, application.transport)}\n"
                
                if application.category == 'cargo':
                    if application.load_capacity:
                        text += f"• Грузоподъемность: {application.load_capacity}\n"
                
                text += f"\n📅 **Время подачи:** {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                
                # Добавляем дополнительную информацию если есть
                if application.additional_info:
                    # Ограничиваем длину дополнительной информации для первого сообщения
                    additional_preview = application.additional_info[:200]
                    if len(application.additional_info) > 200:
                        additional_preview += "..."
                    text += f"\n📝 **Дополнительная информация:**\n{additional_preview}\n"
                
                text += f"\n⚡ **Действия:**"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📋 Подробно", callback_data=f"app_details_{application.id}"),
                        InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{application.id}")
                    ],
                    [
                        InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{application.phone}"),
                        InlineKeyboardButton(text="💬 WhatsApp", url=f"https://wa.me/{application.phone.replace('+', '').replace(' ', '').replace('(', '').replace(')', '').replace('-', '')}")
                    ]
                ])
                
                await bot.send_message(
                    chat_id=manager_telegram_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
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
📊 **НОВАЯ ЗАЯВКА В СИСТЕМЕ**

📋 **#{application.id}** | {self.get_category_text(application.category)}

👤 **{application.full_name}**
📱 {application.phone}
🏙️ {application.city}

⏰ {application.created_at.strftime('%d.%m.%Y %H:%M')}

🔄 Статус: {application.status.value.upper()}
📊 Назначен менеджер: {'Да' if application.assigned_manager_id else 'Ожидает назначения'}
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Подробности", callback_data=f"app_details_{application.id}")],
                [InlineKeyboardButton(text="👥 Все заявки", callback_data="new_applications")]
            ])
            
            for admin_id in settings.ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id, 
                        text=text, 
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
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