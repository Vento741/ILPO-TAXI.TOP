"""
Обработчики для работы с заявками клиентов
"""
import logging
import html
from typing import List, Optional
from aiogram import Router, F
from aiogram.enums import ParseMode
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
    await message.answer("🧪 Тестовая команда работает! Application router активен.", parse_mode=ParseMode.HTML)

@application_router.message(Command("applications"))
async def cmd_applications(message: Message):
    """Показать список заявок менеджера"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Получаем все заявки менеджера (без фильтра по статусу)
        applications = await manager_service.get_manager_applications(telegram_id, limit=10)
        
        if not applications:
            await message.answer(
                "📋 **Список заявок пуст**\n\n"
                "У вас пока нет назначенных заявок.",
                reply_markup=get_applications_empty_keyboard(),
                parse_mode=ParseMode.HTML
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
        
        # Добавляем метку времени, чтобы сообщение всегда было разным
        current_time = datetime.utcnow().strftime('%H:%M:%S')
        text += f"\nОбновлено: {current_time}"
        
        await message.answer(text, reply_markup=get_applications_keyboard(), parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок: {e}")
        await message.answer("❌ Произошла ошибка при получении заявок.", parse_mode=ParseMode.HTML)

# Вспомогательная функция для обработки списка заявок через callback
async def process_applications_callback(
    callback: CallbackQuery, 
    status: Optional[ApplicationStatus] = None,
    page: int = 1,
    show_all: bool = False
):
    """Обработать запрос на показ заявок через callback
    
    Args:
        callback: Объект CallbackQuery
        status: Статус заявок для фильтрации
        page: Номер страницы для пагинации (начиная с 1)
        show_all: Показать все заявки (как для админа)
    """
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Настройки пагинации
        per_page = 5  # Количество заявок на странице
        offset = (page - 1) * per_page
        
        # Получаем заявки менеджера с указанным статусом
        applications = await manager_service.get_manager_applications(
            telegram_id, 
            status=status, 
            limit=per_page, 
            offset=offset,
            show_all=show_all
        )
        
        # Получаем общее количество заявок для пагинации
        all_applications = await manager_service.get_manager_applications(
            telegram_id, 
            status=status,
            limit=1000,  # Большое значение для получения всех заявок
            show_all=show_all
        )
        total_applications = len(all_applications)
        total_pages = (total_applications + per_page - 1) // per_page  # Округление вверх
        
        if not applications:
            try:
                status_text = "Ваши" if status is None else {
                    ApplicationStatus.NEW: "Новые",
                    ApplicationStatus.ASSIGNED: "Назначенные",
                    ApplicationStatus.IN_PROGRESS: "В работе",
                    ApplicationStatus.COMPLETED: "Завершенные"
                }.get(status, "")
                
                await callback.message.edit_text(
                    f"📋 **{status_text} заявки**\n\n"
                    "У вас пока нет заявок в этой категории.",
                    reply_markup=get_applications_empty_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    await callback.answer("✅ Список заявок актуален", parse_mode=ParseMode.HTML)
                else:
                    raise edit_error
            return
        
        # Формируем список заявок
        status_text = "Ваши" if status is None else {
            ApplicationStatus.NEW: "Новые",
            ApplicationStatus.ASSIGNED: "Назначенные",
            ApplicationStatus.IN_PROGRESS: "В работе",
            ApplicationStatus.COMPLETED: "Завершенные"
        }.get(status, "")
        
        if show_all:
            status_text = "Все"
        
        text = f"📋 **{status_text} заявки (стр. {page}/{total_pages}):**\n\n"
        
        for app in applications:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} **Заявка #{app.id}**\n"
            text += f"👤 {app.full_name}\n"
            text += f"📱 {app.phone}\n"
            text += f"🏙️ {app.city}\n"
            text += f"🚗 {category_text}\n"
            text += f"📅 {app.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Добавляем метку времени, чтобы сообщение всегда было разным
        current_time = datetime.utcnow().strftime('%H:%M:%S')
        text += f"\nОбновлено: {current_time}"
        
        # Формируем клавиатуру с кнопками выбора заявки и пагинации
        keyboard_buttons = []
        
        # Кнопки выбора заявок
        for app in applications:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{app.id} - {app.full_name} ({get_status_emoji(app.status)})",
                    callback_data=f"app_details_{app.id}"
                )
            ])
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 1:
            # Кнопка "Назад" для перехода на предыдущую страницу
            callback_data = f"page_{get_status_code(status)}_{page-1}"
            if show_all:
                callback_data += "_all"
            pagination_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)
            )
        
        if page < total_pages:
            # Кнопка "Вперед" для перехода на следующую страницу
            callback_data = f"page_{get_status_code(status)}_{page+1}"
            if show_all:
                callback_data += "_all"
            pagination_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=callback_data)
            )
        
        if pagination_buttons:
            keyboard_buttons.append(pagination_buttons)
        
        # Кнопки управления
        keyboard_buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_{get_status_code(status)}")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ К списку заявок", callback_data="applications_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer("✅ Список заявок обновлен", parse_mode=ParseMode.HTML)
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Список заявок актуален", parse_mode=ParseMode.HTML)
            else:
                raise edit_error
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок: {e}")
        await callback.answer("❌ Произошла ошибка при получении заявок.", parse_mode=ParseMode.HTML)

def get_status_code(status: Optional[ApplicationStatus]) -> str:
    """Получить код статуса для использования в callback_data"""
    if status is None:
        return "all"
    return {
        ApplicationStatus.NEW: "new",
        ApplicationStatus.ASSIGNED: "assigned",
        ApplicationStatus.IN_PROGRESS: "in_progress",
        ApplicationStatus.COMPLETED: "completed",
        ApplicationStatus.WAITING_CLIENT: "waiting",
        ApplicationStatus.CANCELLED: "cancelled"
    }.get(status, "all")

@application_router.callback_query(F.data == "my_applications")
async def callback_my_applications(callback: CallbackQuery):
    """Показать мои заявки"""
    await process_applications_callback(callback)

@application_router.callback_query(F.data == "new_applications")
async def callback_new_applications(callback: CallbackQuery):
    """Показать новые заявки"""
    await process_applications_callback(callback, status=ApplicationStatus.NEW)

@application_router.callback_query(F.data == "assigned_applications")
async def callback_assigned_applications(callback: CallbackQuery):
    """Показать назначенные заявки"""
    await process_applications_callback(callback, status=ApplicationStatus.ASSIGNED)

@application_router.callback_query(F.data == "in_progress_applications")
async def callback_in_progress_applications(callback: CallbackQuery):
    """Показать заявки в работе"""
    await process_applications_callback(callback, status=ApplicationStatus.IN_PROGRESS)

@application_router.callback_query(F.data == "completed_applications")
async def callback_completed_applications(callback: CallbackQuery):
    """Показать завершенные заявки"""
    await process_applications_callback(callback, status=ApplicationStatus.COMPLETED)

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
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
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
                        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                        
                        # Отправляем уведомление клиенту (если есть контакты)
                        await notify_client_about_assignment(application, manager)
                    else:
                        await callback.answer("❌ Заявка не найдена.", parse_mode=ParseMode.HTML)
            else:
                await callback.answer("❌ Не удалось взять заявку. Возможно, её уже взял другой менеджер.", parse_mode=ParseMode.HTML)
        
        elif action == "details":
            # Показать детали заявки
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, app_id)
                
                if application:
                    text = format_application_details(application)
                    keyboard = get_application_detail_keyboard(app_id, False)
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                else:
                    await callback.answer("❌ Заявка не найдена.", parse_mode=ParseMode.HTML)
        
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
                    
                    await callback.message.edit_text(text, reply_markup=get_completed_application_keyboard(), parse_mode=ParseMode.HTML)
                    await callback.answer("✅ Заявка завершена.", parse_mode=ParseMode.HTML)
                else:
                    await callback.answer("❌ Заявка не найдена или не назначена вам.", parse_mode=ParseMode.HTML)
        
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
                    
                    await callback.message.edit_text(contact_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                else:
                    await callback.answer("❌ Заявка не найдена.", parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки действия с заявкой: {e}")
        await callback.answer("❌ Произошла ошибка.", parse_mode=ParseMode.HTML)

@application_router.callback_query(F.data.startswith("app_details_"))
async def callback_application_details(callback: CallbackQuery):
    """Показать детали заявки по ID"""
    app_id = int(callback.data.split("_")[2])
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Получаем заявку из базы данных
        async with AsyncSessionLocal() as session:
            application = await session.get(Application, app_id)
            
            if not application:
                await callback.answer("❌ Заявка не найдена.", parse_mode=ParseMode.HTML)
                return
            
            # Форматируем детальную информацию о заявке
            text = format_application_details(application)
            
            # Определяем доступные действия с заявкой
            is_assigned_to_manager = application.assigned_manager_id == manager.id
            is_new = application.status == ApplicationStatus.NEW and not application.assigned_manager_id
            is_in_progress = application.status in [ApplicationStatus.ASSIGNED, ApplicationStatus.IN_PROGRESS]
            
            # Формируем клавиатуру с действиями
            keyboard_buttons = []
            
            # Кнопка "Взять в работу" для новых заявок
            if is_new or (manager.is_admin and not application.assigned_manager_id):
                keyboard_buttons.append([
                    InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{app_id}")
                ])
            
            # Кнопки для заявок в работе
            if is_assigned_to_manager and is_in_progress:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="📞 Контакты клиента", callback_data=f"app_contact_{app_id}")
                ])
                keyboard_buttons.append([
                    InlineKeyboardButton(text="✅ Завершить заявку", callback_data=f"app_complete_{app_id}")
                ])
                keyboard_buttons.append([
                    InlineKeyboardButton(text="📝 Добавить заметку", callback_data=f"app_note_{app_id}")
                ])
            
            # Кнопка возврата
            keyboard_buttons.append([
                InlineKeyboardButton(text="◀️ Назад к списку", callback_data="applications_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Отправляем детальную информацию
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения деталей заявки: {e}")
        await callback.answer("❌ Произошла ошибка при получении деталей заявки.", parse_mode=ParseMode.HTML)


@application_router.callback_query(F.data.startswith("app_contact_"))
async def callback_application_contact(callback: CallbackQuery):
    """Показать кнопки для связи с клиентом"""
    app_id = int(callback.data.split("_")[2])
    
    try:
        # Получаем заявку, чтобы получить номер телефона
        async with AsyncSessionLocal() as session:
            application = await session.get(Application, app_id)
            if not application or not application.phone:
                await callback.answer("❌ Номер телефона клиента не найден.", show_alert=True)
                return

        # Очищаем номер телефона
        phone_number = ''.join(filter(str.isdigit, application.phone))
        # Для российских номеров, которые могут начинаться с 8, заменяем на 7 для корректной работы ссылок
        if len(phone_number) == 11 and phone_number.startswith('8'):
            phone_number = '7' + phone_number[1:]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 Написать в Telegram", url=f"tg://resolve?phone={phone_number}")],
            [InlineKeyboardButton(text="🟢 Написать в WhatsApp", url=f"https://wa.me/{phone_number}")],
            [InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{phone_number}")],
            [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
        ])
        
        text = (
            f"<b>Выберите способ связи с клиентом:</b>\n\n"
            f"<b>Имя:</b> {html.escape(application.full_name)}\n"
            f"<b>Телефон:</b> <code>{html.escape(application.phone)}</code>"
        )

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Ошибка при отображении контактов: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@application_router.callback_query(F.data == "all_applications")
async def callback_all_applications(callback: CallbackQuery):
    """Показать все заявки в системе"""
    await process_applications_callback(callback, show_all=True)

@application_router.callback_query(F.data == "applications_menu")
async def callback_applications_menu(callback: CallbackQuery):
    """Показать меню заявок"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
        [InlineKeyboardButton(text="📋 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="📋 Назначенные заявки", callback_data="assigned_applications")],
        [InlineKeyboardButton(text="⚙️ В работе", callback_data="in_progress_applications")],
        [InlineKeyboardButton(text="✅ Завершенные", callback_data="completed_applications")],
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="all_applications")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    try:
        await callback.message.edit_text(
            "📋 **Управление заявками**\n\n"
            "Выберите категорию заявок для просмотра:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Меню заявок актуально", parse_mode=ParseMode.HTML)
        else:
            logger.error(f"❌ Ошибка отображения меню заявок: {e}")
            await callback.answer("❌ Произошла ошибка.", parse_mode=ParseMode.HTML)

# Обработчик для пагинации
@application_router.callback_query(F.data.startswith("page_"))
async def callback_pagination(callback: CallbackQuery):
    """Обработка пагинации для списков заявок"""
    data_parts = callback.data.split("_")
    
    # Формат: page_STATUS_НОМЕР[_all]
    if len(data_parts) < 3:
        await callback.answer("❌ Некорректный формат данных пагинации")
        return
    
    status_code = data_parts[1]
    page = int(data_parts[2])
    show_all = len(data_parts) > 3 and data_parts[3] == "all"
    
    # Определяем статус по коду
    status_map = {
        "new": ApplicationStatus.NEW,
        "assigned": ApplicationStatus.ASSIGNED,
        "in_progress": ApplicationStatus.IN_PROGRESS,
        "completed": ApplicationStatus.COMPLETED,
        "waiting": ApplicationStatus.WAITING_CLIENT,
        "cancelled": ApplicationStatus.CANCELLED,
        "all": None
    }
    
    status = status_map.get(status_code)
    
    # Вызываем обработчик с указанной страницей
    await process_applications_callback(callback, status=status, page=page, show_all=show_all)

# Обработчики для обновления списков с разными статусами
@application_router.callback_query(F.data.startswith("refresh_"))
async def callback_refresh_by_status(callback: CallbackQuery):
    """Обновить список заявок с определенным статусом"""
    status_code = callback.data.split("_")[1]
    
    # Определяем статус по коду
    status_map = {
        "new": ApplicationStatus.NEW,
        "assigned": ApplicationStatus.ASSIGNED,
        "in_progress": ApplicationStatus.IN_PROGRESS,
        "completed": ApplicationStatus.COMPLETED,
        "waiting": ApplicationStatus.WAITING_CLIENT,
        "cancelled": ApplicationStatus.CANCELLED,
        "all": None
    }
    
    status = status_map.get(status_code)
    show_all = status_code == "all"
    
    # Вызываем обработчик с указанным статусом
    await process_applications_callback(callback, status=status, show_all=show_all)

def format_application_details(application: Application) -> str:
    """Форматирование детальной информации о заявке с использованием HTML."""
    
    def h(text: Optional[str]) -> str:
        """Экранирует HTML-теги для безопасного отображения."""
        if text is None:
            return ""
        return html.escape(str(text))

    status_emoji = get_status_emoji(application.status)
    category_text = get_category_text(application.category)
    
    text = f"{status_emoji} <b>Заявка #{application.id}</b>\n\n"
    text += f"🚗 <b>Категория:</b> {h(category_text)}\n\n"
    
    text += f"👤 <b>Основная информация:</b>\n"
    text += f"• <b>Имя:</b> {h(application.full_name)}\n"
    text += f"• <b>Телефон:</b> <code>{h(application.phone)}</code>\n"
    text += f"• <b>Возраст:</b> {h(application.age) if application.age else 'Не указан'} лет\n"
    text += f"• <b>Город:</b> {h(application.city)}\n"
    if application.email:
        text += f"• <b>Email:</b> {h(application.email)}\n"
    text += "\n"
    
    # Профессиональная информация
    text += f"🚗 <b>Профессиональная информация:</b>\n"
    
    if application.category in ['driver', 'both', 'cargo']:
        if application.experience:
            text += f"• <b>Стаж вождения:</b> {h(application.experience)} лет\n"
    
    if application.category in ['courier', 'both']:
        if application.transport:
            transport_map = {
                "foot": "🚶 Пеший курьер",
                "bike": "🚴 Велосипед", 
                "scooter": "🛴 Электросамокат",
                "motorcycle": "🏍️ Мотоцикл/скутер",
                "car": "🚗 Автомобиль"
            }
            text += f"• <b>Транспорт:</b> {transport_map.get(application.transport, h(application.transport))}\n"
    
    if application.category == 'cargo':
        if application.load_capacity:
            text += f"• <b>Грузоподъемность:</b> {h(application.load_capacity)}\n"
        if application.vehicle_details:
             text += f"• <b>Детали транспорта:</b> {h(application.vehicle_details)}\n"

    if application.slogan:
        text += f"💬 <b>Слоган:</b> <i>{h(application.slogan)}</i>\n"

    if application.description:
        text += f"📝 <b>О себе:</b>\n{h(application.description)}\n"
        
    text += f"\n📅 <b>Дата подачи:</b> {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"📊 <b>Статус:</b> {h(application.status.value.upper())}\n"
    
    if application.assigned_manager_id:
        text += f"👤 <b>Менеджер:</b> Назначен\n"
    else:
        text += f"👤 <b>Менеджер:</b> Не назначен\n"
    
    if application.processed_at:
        text += f"⚡️ <b>Обработана:</b> {application.processed_at.strftime('%d.%m.%Y %H:%M')}\n"
        
    if application.notes:
        text += f"\n🗒 <b>Заметки менеджера:</b>\n"
        notes_list = sorted(application.notes, key=lambda note: note.created_at, reverse=True)
        for note in notes_list:
            note_date = note.created_at.strftime('%d.%m.%Y %H:%M')
            text += f"  - <i>({note_date})</i>: {h(note.text)}\n"
            
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
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_applications")],
        [InlineKeyboardButton(text="📋 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="📋 Назначенные заявки", callback_data="assigned_applications")],
        [InlineKeyboardButton(text="⚙️ В работе", callback_data="in_progress_applications")],
        [InlineKeyboardButton(text="✅ Завершенные", callback_data="completed_applications")],
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="all_applications")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
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
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Здесь можно реализовать FSM для ввода заметки
        # Пока просто показываем информацию
        await callback.message.edit_text(
            f"📝 **Добавление заметки к заявке #{app_id}**\n\n"
            f"Функция добавления заметок находится в разработке.\n"
            f"Используйте команды для работы с заявкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
            ]),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"❌ Ошибка добавления заметки: {e}")
        await callback.answer("❌ Произошла ошибка.", parse_mode=ParseMode.HTML)

@application_router.callback_query(F.data == "next_application")
async def callback_next_application(callback: CallbackQuery):
    """Показать следующую заявку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Получаем следующую новую заявку
        applications = await manager_service.get_available_new_applications(limit=5)
        
        if not applications:
            await callback.answer("📋 Больше нет новых заявок", parse_mode=ParseMode.HTML)
            return
        
        # Показываем вторую заявку (следующую)
        if len(applications) > 1:
            app = applications[1]
            text = format_application_details(app)
            
            # Создаем клавиатуру с действиями для заявки
            keyboard_buttons = []
            
            # Кнопка "Взять в работу" для новых заявок
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{app.id}")
            ])
            
            # Кнопка "Следующая заявка", если есть еще заявки
            if len(applications) > 2:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="➡️ Следующая заявка", callback_data="next_application")
                ])
            
            # Кнопка возврата
            keyboard_buttons.append([
                InlineKeyboardButton(text="◀️ Назад к списку", callback_data="applications_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await callback.answer("📋 Это была последняя новая заявка", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"❌ Ошибка получения следующей заявки: {e}")
        await callback.answer("❌ Произошла ошибка.", parse_mode=ParseMode.HTML) 