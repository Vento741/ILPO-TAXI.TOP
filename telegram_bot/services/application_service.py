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
from aiogram.enums import ParseMode

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
                logger.info(f"📝 Создание заявки из данных: {application_data}")
                
                # Проверяем обязательные поля
                full_name = application_data.get("full_name", "")
                phone = application_data.get("phone", "")
                age = application_data.get("age")
                city = application_data.get("city", "")
                category = application_data.get("category", "")
                
                if not all([full_name, phone, age, city, category]):
                    logger.error(f"❌ Отсутствуют обязательные поля: full_name={full_name}, phone={phone}, age={age}, city={city}, category={category}")
                    return None
                
                # Обрабатываем массивы из чекбоксов
                delivery_types = application_data.get("deliveryType", [])
                if isinstance(delivery_types, str):
                    delivery_types = [delivery_types]
                
                available_documents = application_data.get("documents", [])
                if isinstance(available_documents, str):
                    available_documents = [available_documents]
                
                # Создаем новую заявку со всеми полями
                new_application = Application(
                    # Основная информация
                    full_name=full_name,
                    phone=phone,
                    age=int(age) if age else None,
                    city=city,
                    category=category,
                    email=application_data.get("email"),
                    
                    # Новые основные поля
                    citizenship=application_data.get("citizenship"),
                    work_status=application_data.get("workStatus"),
                    preferred_time=application_data.get("preferredTime"),
                    work_schedule=application_data.get("workSchedule"),
                    comments=application_data.get("comments"),
                    
                    # Информация для водителей
                    experience=application_data.get("experience"),
                    has_driver_license=application_data.get("hasDriverLicense"),
                    has_car=application_data.get("hasCar"),
                    car_brand=application_data.get("carBrand"),
                    car_model=application_data.get("carModel"),
                    car_year=int(application_data.get("carYear")) if application_data.get("carYear") else None,
                    car_class=application_data.get("carClass"),
                    has_taxi_permit=application_data.get("hasTaxiPermit"),
                    
                    # Информация для курьеров
                    transport=application_data.get("transport"),
                    delivery_types=delivery_types if delivery_types else None,
                    has_thermo_bag=application_data.get("hasThermoBag"),
                    courier_license=application_data.get("courierLicense"),
                    
                    # Информация для грузовых
                    load_capacity=application_data.get("loadCapacity"),
                    truck_type=application_data.get("truckType"),
                    cargo_license=application_data.get("cargoLicense"),
                    
                    # Документы и опыт
                    work_experience=application_data.get("workExperience"),
                    previous_platforms=application_data.get("previousPlatforms"),
                    has_medical_cert=application_data.get("hasMedicalCert"),
                    available_documents=available_documents if available_documents else None,
                    
                    # Согласия
                    has_documents_confirmed=bool(application_data.get("hasDocuments")),
                    agree_terms=bool(application_data.get("agreeTerms")),
                    agree_marketing=bool(application_data.get("agreeMarketing")),
                    
                    # Дополнительная информация (для совместимости)
                    additional_info=self._format_additional_info(application_data),
                    status=ApplicationStatus.NEW
                )
                
                logger.info(f"📝 Объект заявки создан: {new_application}")
                
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
                import traceback
                logger.error(f"Полная ошибка: {traceback.format_exc()}")
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
            from aiogram.enums import ParseMode
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from datetime import timezone, timedelta

            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

            async with AsyncSessionLocal() as session:
                application = await session.get(Application, application_id)
                if not application:
                    return

                phone_number_clean = ''.join(filter(str.isdigit, application.phone))
                if len(phone_number_clean) == 11 and phone_number_clean.startswith('8'):
                    phone_number_clean = '7' + phone_number_clean[1:]

                created_at_msk = "не указано"
                if application.created_at:
                    created_at_msk_dt = application.created_at.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=3)))
                    created_at_msk = created_at_msk_dt.strftime('%d.%m.%Y %H:%M')

                text_parts = [
                    f"🔔 <b>НОВАЯ ЗАЯВКА НАЗНАЧЕНА ВАМ!</b>\n",
                    f"📋 <b>Заявка #{application.id}</b> | {self.get_category_text(application.category)}\n",
                    f"👤 <b>ОСНОВНАЯ ИНФОРМАЦИЯ:</b>",
                    f"  • <b>Имя:</b> {application.full_name}",
                    f"  • <b>Телефон:</b> <a href=\"tel:+{phone_number_clean}\">{application.phone}</a>",
                    f"  • <b>Возраст:</b> {application.age if application.age else 'Не указан'} лет",
                    f"  • <b>Город:</b> {application.city}"
                ]

                if application.email:
                    text_parts.append(f"  • <b>Email:</b> {application.email}")

                if application.citizenship:
                    citizenship_map = {"rf": "🇷🇺 Гражданин РФ", "eaeu": "🌐 Гражданин ЕАЭС", "other": "🌍 Гражданин другой страны"}
                    text_parts.append(f"  • <b>Гражданство:</b> {citizenship_map.get(application.citizenship, application.citizenship)}")

                if application.work_status:
                    status_map = {
                        "self_employed": "💼 Самозанятый (4-6% налог)", "park_self_employed": "🏢 Парковая самозанятость (+10 баллов приоритета)",
                        "ip": "📊 ИП (УСН 6%)", "employee": "📝 Трудовой договор", "not_sure": "❓ Не определился (нужна консультация)"
                    }
                    text_parts.append(f"  • <b>Статус работы:</b> {status_map.get(application.work_status, application.work_status)}")

                # Информация для водителей
                if application.category in ['driver', 'both', 'cargo']:
                    text_parts.append(f"\n🚗 <b>ИНФОРМАЦИЯ О ВОДИТЕЛЕ:</b>\n")
                    
                    if application.experience:
                        text_parts.append(f"  • <b>Стаж вождения:</b> {application.experience} лет")
                    
                    if application.has_driver_license:
                        license_map = {
                            "yes": "✅ Есть права категории B",
                            "getting": "⏳ Получаю права в данный момент",
                            "no": "❌ Нет прав"
                        }
                        text_parts.append(f"  • <b>Водительские права:</b> {license_map.get(application.has_driver_license, application.has_driver_license)}")
                    
                    if application.has_car:
                        car_map = {
                            "own": "🚗 Есть собственный автомобиль",
                            "rent": "🔑 Планирую арендовать",
                            "no": "❌ Нет автомобиля"
                        }
                        text_parts.append(f"  • <b>Автомобиль:</b> {car_map.get(application.has_car, application.has_car)}")
                    
                    # Детали автомобиля
                    if application.car_brand or application.car_model:
                        car_info = ""
                        if application.car_brand:
                            car_info += application.car_brand
                        if application.car_model:
                            car_info += f" {application.car_model}"
                        if application.car_year:
                            car_info += f" ({application.car_year} г.)"
                        if car_info:
                            text_parts.append(f"  • <b>Модель автомобиля:</b> {car_info}")
                    
                    if application.car_class:
                        class_map = {
                            "economy": "💰 Эконом (Lada, KIA Rio, Hyundai Solaris)",
                            "comfort": "⭐ Комфорт (VW Polo, Skoda Rapid, KIA Cerato)",
                            "comfort_plus": "⭐⭐ Комфорт+ (Toyota Camry, KIA Optima)",
                            "business": "💎 Бизнес (BMW 5, Mercedes E, Audi A6)"
                        }
                        text_parts.append(f"  • <b>Желаемый класс:</b> {class_map.get(application.car_class, application.car_class)}")
                    
                    if application.has_taxi_permit:
                        permit_map = {
                            "yes": "✅ Есть разрешение на такси",
                            "getting": "⏳ Оформляю разрешение",
                            "no": "❌ Нет разрешения",
                            "help_needed": "🆘 Нужна помощь в получении"
                        }
                        text_parts.append(f"  • <b>Разрешение такси:</b> {permit_map.get(application.has_taxi_permit, application.has_taxi_permit)}")

                # Информация для курьеров
                if application.category in ['courier', 'both']:
                    text_parts.append(f"\n📦 <b>ИНФОРМАЦИЯ О КУРЬЕРЕ:</b>\n")
                    
                    if application.transport:
                        transport_map = {
                            "foot": "🚶 Пеший курьер",
                            "bike": "🚴 Велосипед",
                            "scooter": "🛴 Электросамокат",
                            "motorcycle": "🏍️ Мотоцикл/скутер",
                            "car": "🚗 Автомобиль"
                        }
                        text_parts.append(f"  • <b>Транспорт:</b> {transport_map.get(application.transport, application.transport)}")
                    
                    if application.delivery_types:
                        delivery_map = {
                            "yandex_food": "🍕 Яндекс.Еда",
                            "yandex_delivery": "📦 Яндекс.Доставка",
                            "yandex_lavka": "🛒 Яндекс.Лавка",
                            "all": "🌟 Все категории"
                        }
                        delivery_list = [delivery_map.get(dt, dt) for dt in application.delivery_types]
                        text_parts.append(f"  • <b>Категории доставки:</b> {', '.join(delivery_list)}")
                    
                    if application.has_thermo_bag:
                        bag_map = {
                            "yes": "✅ Есть термосумка",
                            "buying": "🛒 Планирую купить",
                            "rent": "🔑 Буду арендовать",
                            "no": "❌ Нет термосумки"
                        }
                        text_parts.append(f"  • <b>Термосумка:</b> {bag_map.get(application.has_thermo_bag, application.has_thermo_bag)}")
                    
                    if application.courier_license:
                        courier_license_map = {
                            "yes": "✅ Есть права категории B",
                            "motorcycle": "🏍️ Есть права категории A/A1",
                            "no": "❌ Нет прав"
                        }
                        text_parts.append(f"  • <b>Права (для автокурьера):</b> {courier_license_map.get(application.courier_license, application.courier_license)}")

                # Информация для грузовых
                if application.category == 'cargo':
                    text_parts.append(f"\n🚚 <b>ГРУЗОВЫЕ ПЕРЕВОЗКИ:</b>\n")
                    
                    if application.load_capacity:
                        capacity_map = {
                            "1.5": "📦 До 1,5 тонн (Газель)",
                            "3": "📦📦 До 3 тонн",
                            "5": "📦📦📦 До 5 тонн",
                            "10": "🚚 До 10 тонн",
                            "20": "🚛 До 20 тонн",
                            "20+": "🚛🚛 Более 20 тонн"
                        }
                        text_parts.append(f"  • <b>Грузоподъемность:</b> {capacity_map.get(application.load_capacity, application.load_capacity)}")
                    
                    if application.truck_type:
                        truck_map = {
                            "tent": "🏕️ Тентованный",
                            "closed": "📦 Закрытый",
                            "refrigerator": "🧊 Рефрижератор",
                            "platform": "🚛 Платформа",
                            "dump": "🏗️ Самосвал"
                        }
                        text_parts.append(f"  • <b>Тип кузова:</b> {truck_map.get(application.truck_type, application.truck_type)}")
                    
                    if application.cargo_license:
                        cargo_license_map = {
                            "b": "🚗 Категория B (до 3,5т)",
                            "c": "🚚 Категория C",
                            "ce": "🚛 Категория CE",
                            "no": "❌ Нет прав на грузовой"
                        }
                        text_parts.append(f"  • <b>Права на грузовой:</b> {cargo_license_map.get(application.cargo_license, application.cargo_license)}")

                # Документы и опыт
                text_parts.append(f"\n📄 <b>ДОКУМЕНТЫ И ОПЫТ:</b>\n")
                
                if application.work_experience:
                    exp_map = {
                        "no_experience": "🥉 Нет опыта в такси/доставке",
                        "less_year": "🥉 Менее года",
                        "1_3_years": "🥈 1-3 года",
                        "3_5_years": "🥇 3-5 лет",
                        "more_5_years": "🏆 Более 5 лет"
                    }
                    text_parts.append(f"  • <b>Опыт работы:</b> {exp_map.get(application.work_experience, application.work_experience)}")
                
                if application.previous_platforms:
                    text_parts.append(f"  • <b>Работал в:</b> {application.previous_platforms}")
                
                if application.has_medical_cert:
                    med_map = {
                        "yes": "✅ Есть действующая медсправка",
                        "expired": "⚠️ Справка просрочена",
                        "no": "❌ Нет справки",
                        "help_needed": "🆘 Нужна помощь в получении"
                    }
                    text_parts.append(f"  • <b>Медсправка:</b> {med_map.get(application.has_medical_cert, application.has_medical_cert)}")
                
                if application.available_documents:
                    doc_map = {
                        "passport": "🆔 Паспорт",
                        "driver_license": "🚗 Водительские права",
                        "snils": "📄 СНИЛС",
                        "inn": "📊 ИНН",
                        "car_docs": "🚙 Документы на авто"
                    }
                    docs = [doc_map.get(doc, doc) for doc in application.available_documents]
                    text_parts.append(f"  • <b>Имеющиеся документы:</b> {', '.join(docs)}")

                # Предпочтения и график
                text_parts.append(f"\n⏰ <b>ПРЕДПОЧТЕНИЯ:</b>\n")
                
                if application.preferred_time:
                    time_map = {
                        "9-12": "🌅 09:00-12:00",
                        "12-15": "☀️ 12:00-15:00",
                        "15-18": "🌇 15:00-18:00",
                        "18-21": "🌃 18:00-21:00",
                        "any": "🕐 Любое время"
                    }
                    text_parts.append(f"  • <b>Время звонка:</b> {time_map.get(application.preferred_time, application.preferred_time)}")
                
                if application.work_schedule:
                    schedule_map = {
                        "full_time": "⏰ Полный день (8+ часов)",
                        "part_time": "🕐 Неполный день (4-8 часов)",
                        "weekends": "📅 Только выходные",
                        "evenings": "🌃 Вечерние часы",
                        "flexible": "🔄 Гибкий график"
                    }
                    text_parts.append(f"  • <b>График работы:</b> {schedule_map.get(application.work_schedule, application.work_schedule)}")

                # Согласия
                agreements = []
                if application.has_documents_confirmed:
                    agreements.append("✅ Документы")
                if application.agree_terms:
                    agreements.append("✅ Условия")
                if application.agree_marketing:
                    agreements.append("✅ Рассылка")
                
                if agreements:
                    text_parts.append(f"  • <b>Согласия:</b> {', '.join(agreements)}")

                # Комментарии
                if application.comments:
                    text_parts.append(f"\n💬 <b>КОММЕНТАРИИ КЛИЕНТА:</b>\n<i>{application.comments}</i>")

                # Метаданные
                text_parts.append(f"\n\n📅 <b>ВРЕМЯ ПОДАЧИ:</b> {created_at_msk}")
                text_parts.append(f"⚡ <b>ДЕЙСТВИЯ:</b>")

                text = "\n".join(text_parts)

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{application.id}"),
                        InlineKeyboardButton(text="📊 Подробности", callback_data=f"app_details_{application.id}")
                    ],
                    [
                        InlineKeyboardButton(text="💬 WhatsApp", url=f"https://wa.me/{phone_number_clean}")
                    ]
                ])
                
                await bot.send_message(
                    chat_id=manager_telegram_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                
                logger.info(f"✅ Менеджер {manager_telegram_id} уведомлен о заявке #{application.id}")

        except Exception as e:
            logger.error(f"❌ Ошибка уведомления менеджера: {e}")
            import traceback
            logger.error(f"Полная ошибка: {traceback.format_exc()}")
    
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