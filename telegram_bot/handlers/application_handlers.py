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
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from telegram_bot.services.manager_service import manager_service
from telegram_bot.models.support_models import Application, ApplicationStatus, Manager
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
    """Показать меню управления заявками"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.", parse_mode=ParseMode.HTML)
            return
        
        # Перенаправляем на стандартизированное меню заявок
        keyboard_buttons = [
            [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
            [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="new_applications")],
            [InlineKeyboardButton(text="⚙️ В работе", callback_data="in_progress_applications")],
            [InlineKeyboardButton(text="✅ Завершенные", callback_data="completed_applications")]
        ]
        
        if manager.is_admin:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🗂️ Все заявки (Админ)", callback_data="all_applications")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            "<b>📋 Управление заявками</b>\n\n"
            "Выберите категорию заявок для просмотра:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка отображения меню заявок: {e}")
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
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
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
                    f"📋 <b>{status_text} заявки</b>\n\n"
                    "У вас пока нет заявок в этой категории.",
                    reply_markup=get_applications_empty_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    await callback.answer("✅ Список заявок актуален")
                else:
                    raise edit_error
            return
        
        # Формируем список заявок
        status_text_map = {
            ApplicationStatus.NEW: "Новые",
            ApplicationStatus.ASSIGNED: "Назначенные",
            ApplicationStatus.IN_PROGRESS: "В работе",
            ApplicationStatus.COMPLETED: "Завершенные"
        }
        status_header = "Все" if show_all else status_text_map.get(status, "Ваши")
        
        text = f"<b>📋 {status_header} заявки (стр. {page}/{total_pages}):</b>\n\n"
        
        for app in applications:
            status_emoji = get_status_emoji(app.status)
            category_text = get_category_text(app.category)
            
            text += f"{status_emoji} <b>Заявка #{app.id}</b>\n"
            text += f"👤 {html.escape(app.full_name)}\n"
            text += f"📱 <code>{html.escape(app.phone)}</code>\n"
            text += f"🏙️ {html.escape(app.city)}\n"
            text += f"{category_text}\n" # Эмодзи уже в category_text
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
        page_code = get_status_code(status, show_all)

        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page_code}_{page-1}")
            )
        
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page_{page_code}_{page+1}")
            )
        
        if pagination_buttons:
            keyboard_buttons.append(pagination_buttons)
        
        # Кнопки управления
        refresh_code = get_status_code(status, show_all)
        keyboard_buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_{refresh_code}")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ К списку заявок", callback_data="applications_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer("✅ Список заявок обновлен")
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                await callback.answer("✅ Список заявок актуален")
            else:
                raise edit_error
    
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок: {e}")
        await callback.answer("❌ Произошла ошибка при получении заявок.", show_alert=True)

def get_status_code(status: Optional[ApplicationStatus], show_all: bool = False) -> str:
    """Получить код статуса для использования в callback_data"""
    if status is None:
        return "all_admin" if show_all else "my"
    
    return {
        ApplicationStatus.NEW: "new",
        ApplicationStatus.ASSIGNED: "assigned",
        ApplicationStatus.IN_PROGRESS: "in_progress",
        ApplicationStatus.COMPLETED: "completed",
        ApplicationStatus.WAITING_CLIENT: "waiting",
        ApplicationStatus.CANCELLED: "cancelled"
    }.get(status, "my")

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

@application_router.callback_query(F.data.startswith("app_details_"))
async def callback_application_details(callback: CallbackQuery):
    """Показать детали заявки по ID"""
    app_id = int(callback.data.split("_")[2])
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
            return
        
        # Получаем заявку из базы данных с предзагрузкой менеджера
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Application)
                .options(selectinload(Application.assigned_manager))
                .where(Application.id == app_id)
            )
            application = result.scalars().first()
            
            if not application:
                await callback.answer("❌ Заявка не найдена.", show_alert=True)
                return
            
            # Форматируем детальную информацию о заявке
            text = format_application_details(application)
            
            # Определяем доступные действия с заявкой
            is_assigned_to_current_manager = application.assigned_manager_id == manager.id
            is_new = application.status == ApplicationStatus.NEW and not application.assigned_manager_id
            is_in_progress_by_current_manager = is_assigned_to_current_manager and application.status in [
                ApplicationStatus.ASSIGNED, 
                ApplicationStatus.IN_PROGRESS
            ]
            
            # Формируем клавиатуру с действиями
            keyboard_buttons = []
            
            # Кнопка "Взять в работу" для новых, свободных заявок
            if is_new or (manager.is_admin and not application.assigned_manager_id):
                keyboard_buttons.append([
                    InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"app_take_{app_id}")
                ])
            
            # Кнопки для заявок в работе у ТЕКУЩЕГО менеджера
            if is_in_progress_by_current_manager:
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
        await callback.answer("❌ Произошла ошибка при получении деталей заявки.", show_alert=True)


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
            [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
        ])
        
        text = (
            f"<b>Выберите способ связи с клиентом:</b>\n\n"
            f"<b>Имя:</b> {html.escape(application.full_name)}\n"
            f"<b>Телефон:</b> <a href=\"tel:+{phone_number}\">{html.escape(application.phone)}</a>"
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
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
            return
        
        # Здесь можно реализовать FSM для ввода заметки
        # Пока просто показываем информацию
        await callback.message.edit_text(
            f"📝 <b>Добавление заметки к заявке #{app_id}</b>\n\n"
            f"Функция добавления заметок находится в разработке.\n"
            f"Используйте команды для работы с заявкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к заявке", callback_data=f"app_details_{app_id}")]
            ]),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"❌ Ошибка добавления заметки: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

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
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
            return
        
        if action == "take":
            # Взять заявку в работу
            success = await manager_service.assign_application_to_manager(app_id, telegram_id)
            
            if success:
                # Получаем обновленную заявку с загруженным менеджером
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Application)
                        .options(selectinload(Application.assigned_manager))
                        .where(Application.id == app_id)
                    )
                    application = result.scalars().first()
                    
                    if application:
                        text = f"✅ <b>Заявка принята в работу!</b>\n\n"
                        text += format_application_details(application)
                        
                        keyboard = get_taken_application_keyboard(app_id)
                        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                        
                        # Отправляем уведомление клиенту (если есть контакты)
                        await notify_client_about_assignment(application, manager)
                    else:
                        await callback.answer("❌ Заявка не найдена.", show_alert=True)
            else:
                await callback.answer("❌ Не удалось взять заявку. Возможно, её уже взял другой менеджер.", show_alert=True)
        
        elif action == "complete":
            # Завершить заявку
            async with AsyncSessionLocal() as session:
                application = await session.get(Application, app_id)
                
                if application and application.assigned_manager_id == manager.id:
                    application.status = ApplicationStatus.COMPLETED
                    application.processed_at = datetime.utcnow()
                    await session.commit()
                    
                    text = f"✅ <b>Заявка #{app_id} завершена!</b>\n\n"
                    text += "Спасибо за работу! 👍"
                    
                    await callback.message.edit_text(text, reply_markup=get_completed_application_keyboard(), parse_mode=ParseMode.HTML)
                    await callback.answer("✅ Заявка завершена!")
                else:
                    await callback.answer("❌ Заявка не найдена или не назначена вам.", show_alert=True)
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки действия с заявкой: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

@application_router.callback_query(F.data == "all_applications")
async def callback_all_applications(callback: CallbackQuery):
    """Показать все заявки в системе"""
    await process_applications_callback(callback, show_all=True)

@application_router.callback_query(F.data == "applications_menu")
async def callback_applications_menu(callback: CallbackQuery):
    """Показать меню заявок"""
    telegram_id = callback.from_user.id
    manager = await manager_service.get_manager_by_telegram_id(telegram_id)
    
    if not manager:
        await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
        return
    
    # Стандартизированное меню заявок
    keyboard_buttons = [
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="⚙️ В работе", callback_data="in_progress_applications")],
        [InlineKeyboardButton(text="✅ Завершенные", callback_data="completed_applications")]
    ]
    
    # Добавляем админские функции только для админов
    if manager.is_admin:
        keyboard_buttons.append([
            InlineKeyboardButton(text="🗂️ Все заявки (Админ)", callback_data="all_applications")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    try:
        await callback.message.edit_text(
            "<b>📋 Управление заявками</b>\n\n"
            "Выберите категорию заявок для просмотра:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Меню заявок актуально")
        else:
            logger.error(f"❌ Ошибка отображения меню заявок: {e}")
            await callback.answer("❌ Произошла ошибка.", show_alert=True)

# Обработчик для пагинации
@application_router.callback_query(F.data.startswith("page_"))
async def callback_pagination(callback: CallbackQuery):
    """Обработка пагинации для списков заявок"""
    data_parts = callback.data.split("_")
    
    # Формат: page_STATUS_НОМЕР
    if len(data_parts) < 3:
        await callback.answer("❌ Некорректный формат данных пагинации", show_alert=True)
        return
    
    status_code = data_parts[1]
    page = int(data_parts[2])
    
    # Определяем статус по коду
    status_map = {
        "new": ApplicationStatus.NEW,
        "assigned": ApplicationStatus.ASSIGNED,
        "in_progress": ApplicationStatus.IN_PROGRESS,
        "completed": ApplicationStatus.COMPLETED,
        "waiting": ApplicationStatus.WAITING_CLIENT,
        "cancelled": ApplicationStatus.CANCELLED,
        "my": None,
        "all_admin": None
    }
    
    show_all = status_code == "all_admin"
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
        "my": None,
        "all_admin": None
    }
    
    status = status_map.get(status_code)
    show_all = status_code == "all_admin"
    
    # Вызываем обработчик с указанным статусом
    await process_applications_callback(callback, status=status, show_all=show_all)

def format_application_details(application: Application) -> str:
    """Форматирование детальной информации о заявке с использованием HTML."""

    def h(text: Optional[str]) -> str:
        """Экранирует HTML-теги для безопасного отображения."""
        if text is None:
            return ""
        return html.escape(str(text))

    # --- Обновленные и унифицированные словари для перевода ---
    citizenship_map = {
        "rf": "🇷🇺 Гражданин РФ",
        "eaeu": "🌐 Гражданин ЕАЭС",
        "other": "🌍 Гражданин другой страны"
    }
    work_status_map = {
        "self_employed": "💼 Самозанятый (4-6% налог)",
        "park_self_employed": "🏢 Парковая самозанятость (+10 баллов приоритета)",
        "ip": "📊 ИП (УСН 6%)",
        "employee": "📝 Трудовой договор",
        "not_sure": "❓ Не определился (нужна консультация)"
    }
    schedule_map = {
        "full_time": "⏰ Полный день (8+ часов)",
        "part_time": "🕐 Неполный день (4-8 часов)",
        "weekends": "📅 Только выходные",
        "evenings": "🌃 Вечерние часы",
        "flexible": "🔄 Гибкий график"
    }
    license_map = {
        "yes": "✅ Есть",
        "getting": "⏳ В процессе получения",
        "no": "❌ Нет"
    }
    car_map = {
        "own": "🚗 Собственный",
        "rent": "🔑 Аренда",
        "no": "❌ Нет"
    }
    car_class_map = {
        "economy": "💰 Эконом (Lada, KIA Rio, Hyundai Solaris)",
        "comfort": "⭐ Комфорт (VW Polo, Skoda Rapid, KIA Cerato)",
        "comfort_plus": "⭐⭐ Комфорт+ (Toyota Camry, KIA Optima)",
        "business": "💎 Бизнес (BMW 5, Mercedes E, Audi A6)"
    }
    permit_map = {
        "yes": "✅ Есть разрешение на такси",
        "getting": "⏳ Оформляю разрешение",
        "no": "❌ Нет разрешения",
        "help_needed": "🆘 Нужна помощь в получении"
    }
    experience_map = {
        "no_experience": "🆕 Нет опыта в такси/доставке",
        "less_year": "🥉 Менее года",
        "1_3_years": "🥈 1-3 года",
        "3_5_years": "🥇 3-5 лет",
        "more_5_years": "🏆 Более 5 лет"
    }
    doc_map = {
        "passport": "🆔 Паспорт",
        "driver_license": "🚗 Вод. удостоверение",
        "snils": "📄 СНИЛС",
        "inn": "📊 ИНН",
        "car_docs": "🚙 Документы на авто",
        "medical_cert": "🩺 Мед. справка",
        "work_permit": "🛂 Разрешение на работу"
    }
    status_map = {
        "new": "🆕 Новая", "assigned": "👤 Назначена", "in_progress": "⚙️ В работе",
        "waiting_client": "⏳ Ожидание клиента", "completed": "✅ Завершена", "cancelled": "❌ Отменена"
    }
    transport_map = {
        "foot": "🚶 Пеший курьер", "bike": "🚴 Велосипед", "scooter": "🛴 Электросамокат",
        "motorcycle": "🏍️ Мотоцикл/скутер", "car": "🚗 Автомобиль"
    }
    thermo_bag_map = {
        "yes": "✅ Есть термосумка", "buying": "🛒 Планирую купить",
        "rent": "🔑 Буду арендовать", "no": "❌ Нет термосумки"
    }
    time_map = {
        "9-12": "🌅 09:00-12:00", "12-15": "☀️ 12:00-15:00",
        "15-18": "🌇 15:00-18:00", "18-21": "🌃 18:00-21:00",
        "any": "🕐 Любое время"
    }
    med_cert_map = {
        "yes": "✅ Есть действующая", "expired": "⚠️ Просрочена",
        "no": "❌ Нет", "help_needed": "🆘 Нужна помощь"
    }

    def format_bool(value: Optional[bool]) -> str:
        if value is None: return "Не указано"
        return "✅ Да" if value else "❌ Нет"

    def format_list(items: Optional[list], item_map: dict) -> str:
        if not items: return "Не указано"
        return ", ".join([item_map.get(item, h(item)) for item in items])

    status_emoji = get_status_emoji(application.status)
    category_text = get_category_text(application.category)
    
    text = f"{status_emoji} <b>Заявка #{application.id}</b>\n\n"
    
    # --- Основная информация ---
    text += "👤 <b>ОСНОВНАЯ ИНФОРМАЦИЯ:</b>\n"
    text += f"  • <b>Имя:</b> {h(application.full_name)}\n"
    text += f"  • <b>Телефон:</b> <code>{h(application.phone)}</code>\n"
    if application.email:
        text += f"  • <b>Email:</b> {h(application.email)}\n"
    text += f"  • <b>Город:</b> {h(application.city)}\n"
    if application.age:
        text += f"  • <b>Возраст:</b> {h(str(application.age))} лет\n"
    if application.citizenship:
        text += f"  • <b>Гражданство:</b> {citizenship_map.get(application.citizenship, h(application.citizenship))}\n"

    # --- Рабочие предпочтения ---
    text += "\n🗓 <b>РАБОЧИЕ ПРЕДПОЧТЕНИЯ:</b>\n"
    if application.work_status:
        text += f"  • <b>Статус:</b> {work_status_map.get(application.work_status, h(application.work_status))}\n"
    if application.work_schedule:
        text += f"  • <b>График:</b> {schedule_map.get(application.work_schedule, h(application.work_schedule))}\n"
    if application.preferred_time:
        text += f"  • <b>Время для звонка:</b> {time_map.get(application.preferred_time, h(application.preferred_time))}\n"

    # --- Информация для водителей ---
    if application.category in ['driver', 'both', 'cargo']:
        text += f"\n🚗 <b>ИНФОРМАЦИЯ О ВОДИТЕЛЕ:</b>\n"
        if application.experience:
            text += f"  • <b>Стаж вождения:</b> {h(application.experience)} лет\n"
        if application.has_driver_license:
            text += f"  • <b>Права:</b> {license_map.get(application.has_driver_license, h(application.has_driver_license))}\n"
        if application.has_car:
            text += f"  • <b>Свой авто:</b> {car_map.get(application.has_car, h(application.has_car))}\n"
        if application.car_brand and application.car_model:
            car_year = f" ({application.car_year} г.)" if application.car_year else ""
            text += f"  • <b>Автомобиль:</b> {h(application.car_brand)} {h(application.car_model)}{h(car_year)}\n"
        if application.car_class:
            text += f"  • <b>Желаемый класс:</b> {car_class_map.get(application.car_class, h(application.car_class))}\n"
        if application.has_taxi_permit:
            text += f"  • <b>Разрешение такси:</b> {permit_map.get(application.has_taxi_permit, h(application.has_taxi_permit))}\n"

    # --- Информация для курьеров ---
    if application.category in ['courier', 'both']:
        text += f"\n📦 <b>ИНФОРМАЦИЯ О КУРЬЕРЕ:</b>\n"
        if application.transport:
            text += f"  • <b>Транспорт:</b> {transport_map.get(application.transport, h(application.transport))}\n"
        if application.has_thermo_bag:
            text += f"  • <b>Термосумка:</b> {thermo_bag_map.get(application.has_thermo_bag, h(application.has_thermo_bag))}\n"
        if application.courier_license:
             text += f"  • <b>Права (курьер):</b> {license_map.get(application.courier_license, h(application.courier_license))}\n"
    
    # --- Информация для грузовых ---
    if application.category == 'cargo':
        text += f"\n🚛 <b>ГРУЗОВЫЕ ПЕРЕВОЗКИ:</b>\n"
        if application.load_capacity:
            text += f"  • <b>Грузоподъемность:</b> {h(application.load_capacity)}\n"
        if application.truck_type:
            text += f"  • <b>Тип кузова:</b> {h(application.truck_type)}\n"
        if application.cargo_license:
            text += f"  • <b>Права (грузовые):</b> {h(application.cargo_license)}\n"

    # --- Опыт и документы ---
    text += "\n🗂 <b>ОПЫТ И ДОКУМЕНТЫ:</b>\n"
    if application.work_experience:
        text += f"  • <b>Опыт в сфере:</b> {experience_map.get(application.work_experience, h(application.work_experience))}\n"
    if application.previous_platforms:
        text += f"  • <b>Работал в:</b> {h(application.previous_platforms)}\n"
    if application.has_medical_cert:
        text += f"  • <b>Мед. справка:</b> {med_cert_map.get(application.has_medical_cert, h(application.has_medical_cert))}\n"
    if application.available_documents:
        text += f"  • <b>Документы:</b> {format_list(application.available_documents, doc_map)}\n"
    
    # --- Комментарий клиента ---
    if application.comments:
        text += f"\n💬 <b>КОММЕНТАРИЙ КЛИЕНТА:</b>\n<i>{h(application.comments)}</i>\n"
    
    # --- Служебная информация ---
    text += f"\n- - - - - - - - - - - - - - - - - -\n"
    text += f"<b>Статус:</b> {status_map.get(application.status.value, h(application.status.value.upper()))}\n"
    text += f"<b>Подана:</b> {application.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    if application.processed_at:
        text += f"<b>Обработана:</b> {application.processed_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    if application.assigned_manager:
        text += f"<b>Менеджер:</b> {h(application.assigned_manager.first_name)} {h(application.assigned_manager.last_name or '')}\n"
    else:
        text += f"<b>Менеджер:</b> Не назначен\n"
    
    # --- Согласия ---
    text += "\n⚖️ <b>СОГЛАСИЯ:</b>\n"
    text += f"  • <b>Наличие документов:</b> {format_bool(application.has_documents_confirmed)}\n"
    text += f"  • <b>Условия работы:</b> {format_bool(application.agree_terms)}\n"
    text += f"  • <b>Рассылка:</b> {format_bool(application.agree_marketing)}\n"
    
    if application.notes:
        text += f"\n🗒 <b>Заметки менеджера:</b>\n<i>{h(application.notes)}</i>\n"
    
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



def get_applications_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пустого списка заявок"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_applications")],
        [InlineKeyboardButton(text="◀️ Управление заявками", callback_data="applications_menu")]
    ])

def get_taken_application_keyboard(app_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для взятой в работу заявки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить заявку", callback_data=f"app_complete_{app_id}")],
        [InlineKeyboardButton(text="📞 Связаться с клиентом", callback_data=f"app_contact_{app_id}")],
        [InlineKeyboardButton(text="📝 Добавить заметку", callback_data=f"app_note_{app_id}")],
        [InlineKeyboardButton(text="◀️ Управление заявками", callback_data="applications_menu")]
    ])

def get_completed_application_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для завершенной заявки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Управление заявками", callback_data="applications_menu")],
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
            result = await session.execute(
                select(Application).where(Application.status == ApplicationStatus.NEW)
                .options(selectinload(Application.assigned_manager))
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
                        
                        # Обновляем объект в памяти, чтобы избежать lazy load ошибки
                        app.assigned_manager = available_manager
                        
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
🔔 <b>Новая заявка назначена вам!</b>

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

@application_router.callback_query(F.data == "next_application")
async def callback_next_application(callback: CallbackQuery):
    """Показать следующую заявку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.", show_alert=True)
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
            await callback.answer("📋 Это была последняя новая заявка")
    except Exception as e:
        logger.error(f"❌ Ошибка получения следующей заявки: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True) 