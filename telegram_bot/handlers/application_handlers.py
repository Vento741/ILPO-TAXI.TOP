"""
Обработчики для работы с заявками клиентов
"""
import logging
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime

from telegram_bot.services.manager_service import manager_service
from telegram_bot.models.support_models import Application, ApplicationStatus
from telegram_bot.models.database import AsyncSessionLocal
from telegram_bot.config.settings import settings

logger = logging.getLogger(__name__)

# Создаем роутер для заявок
application_router = Router()

# Тестовая команда для отладки
@application_router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда для отладки"""
    await message.answer("🧪 Тестовая команда работает! Application router активен.")

@application_router.message(Command("applications"))
async def cmd_applications(message: Message):
    """Показать список заявок менеджера"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем все заявки менеджера (без фильтра по статусу)
        applications = await manager_service.get_manager_applications(telegram_id, limit=10)
        
        if not applications:
            await message.answer(
                "📋 **Список заявок пуст**\n\n"
                "У вас пока нет назначенных заявок.",
                reply_markup=get_applications_empty_keyboard()
            )
            return
        
        # Формируем список заявок
        text = "📋 **Ваши заявки:**\n\n"
        
        for app in applications:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} **Заявка #{app.id}**\n"
            text += f"👤 {app.full_name}\n"
            text += f"📱 {app.phone}\n"
            text += f"🏙️ {app.city}\n"
            text += f"🚗 {category_text}\n"
            text += f"📅 {app.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        await message.answer(text, reply_markup=get_applications_keyboard())
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок: {e}")
        await message.answer("❌ Произошла ошибка при получении заявок.")

@application_router.callback_query(F.data == "new_applications")
async def callback_new_applications(callback: CallbackQuery):
    """Показать новые заявки"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем новые неназначенные заявки
        applications = await manager_service.get_available_new_applications(limit=5)
        
        if not applications:
            try:
                await callback.message.edit_text(
                    "📋 **Новых заявок нет**\n\n"
                    "Все новые заявки уже обработаны или назначены другим менеджерам.",
                    reply_markup=get_applications_empty_keyboard()
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    await callback.answer("✅ Список заявок актуален")
                else:
                    raise edit_error
            return
        
        # Показываем первую заявку детально
        app = applications[0]
        text = format_application_details(app)
        
        keyboard = get_application_detail_keyboard(app.id, len(applications) > 1)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Заявка актуальна")
            else:
                raise edit_error
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения новых заявок: {e}")
        await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data.startswith("app_"))
async def callback_application_action(callback: CallbackQuery):
    """Обработка действий с заявками"""
    data = callback.data.split("_")
    action = data[1]
    app_id = int(data[2])
    
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        if action == "take":
            # Взять заявку в работу
            success = await manager_service.assign_application_to_manager(app_id, telegram_id)
            
            if success:
                # Получаем обновленную заявку
                async with AsyncSessionLocal() as session:
                    application = await session.get(Application, app_id)
                    
                    if application:
                        text = f"✅ **Заявка принята в работу!**\n\n"
                        text += format_application_details(application)
                        
                        keyboard = get_taken_application_keyboard(app_id)
                        await callback.message.edit_text(text, reply_markup=keyboard)
                        
                        # Отправляем уведомление клиенту (если есть контакты)
                        await notify_client_about_assignment(application, manager)
                    else:
                        await callback.answer("❌ Заявка не найдена.")
            else:
                await callback.answer("❌ Не удалось взять заявку. Возможно, её уже взял другой менеджер.")
        
        elif action == "details":
            # Показать детали заявки
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, app_id)
                
                if application:
                    text = format_application_details(application)
                    keyboard = get_application_detail_keyboard(app_id, False)
                    await callback.message.edit_text(text, reply_markup=keyboard)
                else:
                    await callback.answer("❌ Заявка не найдена.")
        
        elif action == "complete":
            # Завершить заявку
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, app_id)
                
                if application and application.assigned_manager_id == manager.id:
                    application.status = ApplicationStatus.COMPLETED
                    application.processed_at = datetime.utcnow()
                    await session.commit()
                    
                    text = f"✅ **Заявка #{app_id} завершена!**\n\n"
                    text += "Спасибо за работу! 👍"
                    
                    await callback.message.edit_text(text, reply_markup=get_completed_application_keyboard())
                    await callback.answer("✅ Заявка завершена!")
                else:
                    await callback.answer("❌ Заявка не найдена или не назначена вам.")
        
        elif action == "contact":
            # Связаться с клиентом
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, app_id)
                
                if application:
                    contact_text = f"""
📞 **Контакты клиента:**

👤 **Имя:** {application.full_name}
📱 **Телефон:** {application.phone}
🏙️ **Город:** {application.city}

Вы можете позвонить клиенту или написать в WhatsApp/Telegram.
                    """
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"📞 {application.phone}", callback_data=f"phone_{application.id}")],
                        [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
                    ])
                    
                    await callback.message.edit_text(contact_text, reply_markup=keyboard)
                else:
                    await callback.answer("❌ Заявка не найдена.")
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки действия с заявкой: {e}")
        await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data == "my_applications")
async def callback_my_applications(callback: CallbackQuery):
    """Показать мои заявки"""
    try:
        await cmd_applications(callback.message)
        await callback.answer()
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Список заявок актуален")
        else:
            logger.error(f"❌ Ошибка при отображении заявок: {e}")
            await callback.answer("❌ Произошла ошибка.")

# ДОБАВЛЯЮ НЕДОСТАЮЩИЕ ОБРАБОТЧИКИ ДЛЯ ЗАЯВОК:

@application_router.callback_query(F.data == "in_progress_applications")
async def callback_in_progress_applications(callback: CallbackQuery):
    """Показать заявки в работе"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем заявки в работе
        applications = await manager_service.get_manager_applications(
            telegram_id, 
            status=ApplicationStatus.IN_PROGRESS, 
            limit=10
        )
        
        if not applications:
            try:
                await callback.message.edit_text(
                    "⚙️ **Заявки в работе**\n\n"
                    "У вас нет заявок в работе.",
                    reply_markup=get_applications_empty_keyboard()
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    await callback.answer("✅ Список заявок актуален")
                else:
                    raise edit_error
            return
        
        text = "⚙️ **Заявки в работе:**\n\n"
        
        for app in applications:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} **Заявка #{app.id}**\n"
            text += f"👤 {app.full_name}\n"
            text += f"📱 {app.phone}\n"
            text += f"🏙️ {app.city}\n"
            text += f"🚗 {category_text}\n"
            text += f"📅 {app.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="in_progress_applications")],
            [InlineKeyboardButton(text="📋 Все заявки", callback_data="my_applications")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        try:
            # Добавляем метку времени, чтобы сообщение всегда было разным
            current_time = datetime.utcnow().strftime('%H:%M:%S')
            text += f"\n\nОбновлено: {current_time}"
            
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Список заявок актуален")
            else:
                raise edit_error
                
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок в работе: {e}")
        await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data == "completed_applications")
async def callback_completed_applications(callback: CallbackQuery):
    """Показать завершенные заявки"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем завершенные заявки
        applications = await manager_service.get_manager_applications(
            telegram_id, 
            status=ApplicationStatus.COMPLETED, 
            limit=10
        )
        
        if not applications:
            try:
                await callback.message.edit_text(
                    "✅ **Завершенные заявки**\n\n"
                    "У вас нет завершенных заявок.",
                    reply_markup=get_applications_empty_keyboard()
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    await callback.answer("✅ Список заявок актуален")
                else:
                    raise edit_error
            return
        
        text = "✅ **Завершенные заявки:**\n\n"
        
        for app in applications:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} **Заявка #{app.id}**\n"
            text += f"👤 {app.full_name}\n"
            text += f"📱 {app.phone}\n"
            text += f"🏙️ {app.city}\n"
            text += f"🚗 {category_text}\n"
            text += f"📅 {app.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="completed_applications")],
            [InlineKeyboardButton(text="📋 Все заявки", callback_data="my_applications")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        try:
            # Добавляем метку времени, чтобы сообщение всегда было разным
            current_time = datetime.utcnow().strftime('%H:%M:%S')
            text += f"\n\nОбновлено: {current_time}"
            
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Список заявок актуален")
            else:
                raise edit_error
                
    except Exception as e:
        logger.error(f"❌ Ошибка получения завершенных заявок: {e}")
        await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data == "refresh_applications")
async def callback_refresh_applications(callback: CallbackQuery):
    """Обновить список заявок"""
    try:
        await cmd_applications(callback.message)
        await callback.answer("✅ Список заявок обновлен")
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Список заявок актуален")
        else:
            logger.error(f"❌ Ошибка при обновлении заявок: {e}")
            await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data == "next_application")
async def callback_next_application(callback: CallbackQuery):
    """Показать следующую заявку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем следующую новую заявку
        applications = await manager_service.get_available_new_applications(limit=5)
        
        if not applications:
            await callback.answer("📋 Больше нет новых заявок")
            return
        
        # Показываем вторую заявку (следующую)
        if len(applications) > 1:
            app = applications[1]
            text = format_application_details(app)
            keyboard = get_application_detail_keyboard(app.id, len(applications) > 2)
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer("📋 Это была последняя новая заявка")
    except Exception as e:
        logger.error(f"❌ Ошибка получения следующей заявки: {e}")
        await callback.answer("❌ Произошла ошибка.")

# Обработчик для добавления заметок к заявкам
@application_router.callback_query(F.data.startswith("app_note_"))
async def callback_application_note(callback: CallbackQuery):
    """Добавить заметку к заявке"""
    app_id = int(callback.data.split("_")[2])
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Здесь можно реализовать FSM для ввода заметки
        # Пока просто показываем информацию
        await callback.message.edit_text(
            f"📝 **Добавление заметки к заявке #{app_id}**\n\n"
            f"Функция добавления заметок находится в разработке.\n"
            f"Используйте команды для работы с заявкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"❌ Ошибка добавления заметки: {e}")
        await callback.answer("❌ Произошла ошибка.")

@application_router.callback_query(F.data == "all_applications")
async def callback_all_applications(callback: CallbackQuery):
    """Показать все заявки в системе"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем все заявки (без фильтра по статусу и менеджеру)
        applications = await manager_service.get_all_applications(limit=15)
        
        if not applications:
            await callback.message.edit_text(
                "📋 **Все заявки системы**\n\n"
                "В системе нет заявок.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="all_applications")],
                    [InlineKeyboardButton(text="◀️ К списку заявок", callback_data="my_applications")]
                ])
            )
            return
        
        text = f"📋 **Все заявки системы ({len(applications)})**\n\n"
        
        for app in applications[:10]:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} **Заявка #{app.id}**\n"
            text += f"👤 {app.full_name}\n"
            text += f"📱 {app.phone}\n"
            text += f"🏙️ {app.city}\n"
            text += f"🚗 {category_text}\n"
            
            # Показываем менеджера, если заявка назначена
            if app.assigned_manager_id:
                text += f"👤 Менеджер: Назначен\n"
            else:
                text += f"👤 Менеджер: Не назначен\n"
                
            text += f"📅 {app.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if len(applications) > 10:
            text += f"... и еще {len(applications) - 10} заявок"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="all_applications")],
            [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        try:
            # Добавляем метку времени, чтобы сообщение всегда было разным
            current_time = datetime.utcnow().strftime('%H:%M:%S')
            text += f"\n\nОбновлено: {current_time}"
            
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as edit_error:
            # Если ошибка связана с тем, что сообщение не изменилось
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Список заявок актуален")
            else:
                # Другие ошибки пробрасываем дальше
                raise edit_error
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех заявок: {e}")
        await callback.answer("❌ Произошла ошибка при получении заявок.")

def format_application_details(application: Application) -> str:
    """Форматирование детальной информации о заявке"""
    status_emoji = get_status_emoji(application.status)
    category_text = get_category_text(application.category)
    
    text = f"{status_emoji} **Заявка #{application.id}**\n\n"
    text += f"🚗 **Категория:** {category_text}\n\n"
    
    text += f"👤 **Основная информация:**\n"
    text += f"• Имя: {application.full_name}\n"
    text += f"• Телефон: {application.phone}\n"
    text += f"• Возраст: {application.age if application.age else 'Не указан'} лет\n"
    text += f"• Город: {application.city}\n"
    if application.email:
        text += f"• Email: {application.email}\n"
    text += "\n"
    
    # Профессиональная информация
    text += f"🚗 **Профессиональная информация:**\n"
    
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
    
    text += f"\n📅 **Дата подачи:** {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"📊 **Статус:** {application.status.value.upper()}\n"
    
    if application.assigned_manager_id:
        text += f"👤 **Менеджер:** Назначен\n"
    else:
        text += f"👤 **Менеджер:** Не назначен\n"
    
    if application.processed_at:
        text += f"⚡️ **Обработана:** {application.processed_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    # Дополнительная информация из новых полей
    text += f"\n📝 **Дополнительная информация:**\n"
    
    # Гражданство
    if application.citizenship:
        citizenship_map = {
            "rf": "Гражданин РФ",
            "eaeu": "Гражданин ЕАЭС",
            "other": "Другое гражданство"
        }
        text += f"• Гражданство: {citizenship_map.get(application.citizenship, application.citizenship)}\n"
    
    # Статус работы
    if application.work_status:
        text += f"• Статус работы: {application.work_status}\n"
    
    # Водительские права
    if application.has_driver_license:
        text += f"• Водительские права: {application.has_driver_license}\n"
    
    # Автомобиль
    if application.has_car:
        text += f"• Автомобиль: {application.has_car}\n"
    
    # Марка и модель
    if application.car_brand and application.car_model:
        car_year = f" ({application.car_year} г.)" if application.car_year else ""
        text += f"• Автомобиль: {application.car_brand} {application.car_model}{car_year}\n"
    
    # Класс автомобиля
    if application.car_class:
        text += f"• Желаемый класс: {application.car_class}\n"
    
    # Разрешение такси
    if application.has_taxi_permit:
        text += f"• Разрешение такси: {application.has_taxi_permit}\n"
    
    # Опыт работы
    if application.work_experience:
        text += f"• Опыт работы: {application.work_experience}\n"
    
    # Предыдущие платформы
    if application.previous_platforms:
        text += f"• Работал в: {application.previous_platforms}\n"
    
    # Медсправка
    if application.has_medical_cert:
        text += f"• Медсправка: {application.has_medical_cert}\n"
    
    # Доступные документы
    if application.available_documents:
        if isinstance(application.available_documents, list):
            text += f"• Документы: {', '.join(application.available_documents)}\n"
        elif isinstance(application.available_documents, dict):
            text += f"• Документы: {', '.join(application.available_documents.values())}\n"
    
    # Курьерская информация
    if application.category in ['courier', 'both']:
        if application.delivery_types:
            if isinstance(application.delivery_types, list):
                text += f"• Категории доставки: {', '.join(application.delivery_types)}\n"
            elif isinstance(application.delivery_types, dict):
                text += f"• Категории доставки: {', '.join(application.delivery_types.values())}\n"
        
        if application.has_thermo_bag:
            text += f"• Термосумка: {application.has_thermo_bag}\n"
    
    # Грузовые перевозки
    if application.category == 'cargo':
        if application.truck_type:
            text += f"• Тип кузова: {application.truck_type}\n"
        if application.cargo_license:
            text += f"• Права: {application.cargo_license}\n"
    
    # График работы
    if application.work_schedule:
        text += f"• График работы: {application.work_schedule}\n"
    
    # Удобное время
    if application.preferred_time:
        text += f"• Удобное время: {application.preferred_time}\n"
    
    # Комментарии
    if application.comments:
        text += f"• Комментарии: {application.comments}\n"
    
    # Согласия
    if application.has_documents_confirmed:
        text += f"• Подтверждение документов: Да\n"
    if application.agree_terms:
        text += f"• Согласие с условиями: Да\n"
    if application.agree_marketing:
        text += f"• Согласие на рассылку: Да\n"
    
    # Старое поле дополнительной информации (для совместимости)
    if application.additional_info:
        # Показываем всю дополнительную информацию без ограничений
        info_lines = application.additional_info.split('\n')
        for line in info_lines:
            if line.strip():
                text += f"• {line.strip()}\n"
    
    if application.notes:
        text += f"\n📝 **Заметки менеджера:**\n{application.notes}\n"
    
    return text

def get_status_emoji(status: ApplicationStatus) -> str:
    """Получить эмодзи для статуса заявки"""
    status_emojis = {
        ApplicationStatus.NEW: "🆕",
        ApplicationStatus.ASSIGNED: "👤",
        ApplicationStatus.IN_PROGRESS: "⚙️",
        ApplicationStatus.WAITING_CLIENT: "⏳",
        ApplicationStatus.COMPLETED: "✅",
        ApplicationStatus.CANCELLED: "❌"
    }
    return status_emojis.get(status, "❓")

def get_category_text(category: str) -> str:
    """Получить текстовое описание категории"""
    categories = {
        "driver": "🚗 Водитель",
        "courier": "📦 Курьер",
        "both": "🚗📦 Водитель и курьер",
        "cargo": "🚛 Грузоперевозки"
    }
    return categories.get(category, category)

def get_applications_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для списка заявок"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="⚙️ В работе", callback_data="in_progress_applications")],
        [InlineKeyboardButton(text="✅ Завершенные", callback_data="completed_applications")],
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="all_applications")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_applications")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
    ])

def get_applications_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пустого списка заявок"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_applications")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
    ])

def get_application_detail_keyboard(app_id: int, has_more: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для детального просмотра заявки"""
    buttons = [
        [InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{app_id}")],
        [InlineKeyboardButton(text="📞 Контакты клиента", callback_data=f"app_contact_{app_id}")],
    ]
    
    if has_more:
        buttons.append([InlineKeyboardButton(text="➡️ Следующая заявка", callback_data="next_application")])
    
    buttons.append([InlineKeyboardButton(text="◀️ К списку заявок", callback_data="my_applications")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_taken_application_keyboard(app_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для взятой в работу заявки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить заявку", callback_data=f"app_complete_{app_id}")],
        [InlineKeyboardButton(text="📞 Связаться с клиентом", callback_data=f"app_contact_{app_id}")],
        [InlineKeyboardButton(text="📝 Добавить заметку", callback_data=f"app_note_{app_id}")],
        [InlineKeyboardButton(text="◀️ К списку заявок", callback_data="my_applications")]
    ])

def get_completed_application_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершенной заявки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
    ])

async def notify_client_about_assignment(application: Application, manager):
    """Уведомить клиента о назначении менеджера"""
    try:
        # Здесь можно добавить отправку SMS или push-уведомления
        # Пока просто логируем
        logger.info(f"📩 Клиент {application.full_name} уведомлен о назначении менеджера {manager.first_name}")
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления клиента: {e}")

# Автоматическое назначение заявок
async def auto_assign_new_applications():
    """Автоматическое назначение новых заявок доступным менеджерам"""
    if not settings.AUTO_ASSIGN_MANAGERS:
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Получаем новые заявки
            from sqlalchemy import select
            result = await session.execute(
                select(Application).where(Application.status == ApplicationStatus.NEW)
            )
            new_applications = result.scalars().all()
            
            for app in new_applications:
                # Ищем доступного менеджера
                available_manager = await manager_service.get_available_manager()
                
                if available_manager:
                    # Назначаем заявку
                    success = await manager_service.assign_application_to_manager(
                        app.id, 
                        available_manager.telegram_id
                    )
                    
                    if success:
                        logger.info(f"✅ Заявка #{app.id} автоматически назначена менеджеру {available_manager.first_name}")
                        
                        # Отправляем уведомление менеджеру
                        await notify_manager_about_new_application(available_manager, app)
    
    except Exception as e:
        logger.error(f"❌ Ошибка автоназначения заявок: {e}")

async def notify_manager_about_new_application(manager, application: Application):
    """Уведомить менеджера о новой заявке"""
    try:
        from aiogram import Bot
        from telegram_bot.config.settings import settings
        
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        text = f"""
🔔 **Новая заявка назначена вам!**

{format_application_details(application)}

Перейдите в бот для обработки заявки.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Открыть заявку", callback_data=f"app_details_{application.id}")],
            [InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{application.id}")]
        ])
        
        await bot.send_message(
            chat_id=manager.telegram_id,
            text=text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления менеджера: {e}") 