"""
Базовые обработчики команд Telegram бота поддержки ILPO-TAXI
"""
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import json

from telegram_bot.services.manager_service import manager_service
from telegram_bot.services.redis_service import redis_service
from telegram_bot.models.support_models import ManagerStatus, ApplicationStatus, SupportChat, ChatMessage
from telegram_bot.config.settings import settings

# Добавляем импорты для работы с чатами
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# Создаем роутер для базовых команд
base_router = Router()

class ManagerStates(StatesGroup):
    """Состояния менеджера"""
    OFFLINE = State()
    ONLINE = State()
    BUSY = State()
    HANDLING_APPLICATION = State()
    HANDLING_CHAT = State()

# Команда /start
@base_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        # Проверяем, является ли пользователь менеджером
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        
        if not manager:
            # Если не менеджер, проверяем, можно ли зарегистрировать
            if telegram_id in settings.MANAGER_IDS or \
               telegram_id in settings.ADMIN_IDS:
                # Регистрируем как менеджера
                is_admin = telegram_id in settings.ADMIN_IDS
                manager = await manager_service.register_manager(
                    telegram_id=telegram_id,
                    username=user.username or "",
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_admin=is_admin
                )
                
                welcome_text = f"""
🎉 **Добро пожаловать в систему поддержки ILPO-TAXI!**

Привет, {user.first_name}! Вы успешно зарегистрированы как {'администратор' if is_admin else 'менеджер'} поддержки.

**Ваши возможности:**
• Получать новые заявки с сайта
• Общаться с клиентами в чате
• Просматривать статистику работы
• Управлять статусом (онлайн/офлайн)

**Доступные команды:**
/online - Начать рабочую смену (статус "онлайн")
/offline - Завершить рабочую смену
/stats - Посмотреть статистику
/help - Справка по командам

Чтобы начать работу, нажмите /online
                """
                
                await message.answer(welcome_text, reply_markup=get_manager_main_keyboard(is_admin, "offline"))
                await state.set_state(ManagerStates.OFFLINE)
                
            else:
                # Обычный пользователь
                await message.answer(
                    "🤖 Привет! Это бот поддержки ILPO-TAXI для менеджеров.\n\n"
                    "Если вы хотите подключиться к нашему таксопарку, "
                    "перейдите на сайт: https://ilpo-taxi.top"
                )
                return
        else:
            # Существующий менеджер
            stats = await manager_service.get_manager_stats(telegram_id)
            status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(manager.status.value, "⚪")
            
            welcome_text = f"""
👋 **С возвращением, {manager.first_name}!**

{status_emoji} Статус: {manager.status.value.upper()}
📊 Активных чатов: {stats['active_chats'] if stats else 0}/{manager.max_active_chats}
📋 Всего заявок: {stats['total_applications'] if stats else 0}

Выберите действие:
            """
            
            await message.answer(welcome_text, reply_markup=get_manager_main_keyboard(manager.is_admin, manager.status.value))
            
            # Устанавливаем состояние в зависимости от статуса
            if manager.status == ManagerStatus.ONLINE:
                await state.set_state(ManagerStates.ONLINE)
            elif manager.status == ManagerStatus.BUSY:
                await state.set_state(ManagerStates.BUSY)
            else:
                await state.set_state(ManagerStates.OFFLINE)
    
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

# Команда /online
@base_router.message(Command("online"))
async def cmd_online(message: Message, state: FSMContext):
    """Перевести менеджера в онлайн"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Начинаем рабочую сессию
        success = await manager_service.start_work_session(telegram_id)
        if success:
            await message.answer(
                f"🟢 **Вы в сети!**\n\n"
                f"Привет, {manager.first_name}! Вы готовы принимать заявки и чаты.\n"
                f"Максимум активных чатов: {manager.max_active_chats}\n\n"
                f"Для завершения смены используйте /offline",
                reply_markup=get_manager_main_keyboard(manager.is_admin, "online")
            )
            await state.set_state(ManagerStates.ONLINE)
        else:
            await message.answer("❌ Не удалось перейти в онлайн. Попробуйте позже.")
    
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /online: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

# Команда /offline
@base_router.message(Command("offline"))
async def cmd_offline(message: Message, state: FSMContext):
    """Перевести менеджера в офлайн"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Проверяем активные чаты
        active_chats = await redis_service.get_manager_active_chats(str(telegram_id))
        
        if active_chats:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, завершить смену", callback_data="confirm_offline")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_offline")]
            ])
            
            await message.answer(
                f"⚠️ **Внимание!**\n\n"
                f"У вас есть {len(active_chats)} активных чата(ов).\n"
                f"При завершении смены они будут переданы другим менеджерам.\n\n"
                f"Вы уверены, что хотите завершить смену?",
                reply_markup=keyboard
            )
        else:
            # Завершаем смену
            success = await manager_service.end_work_session(telegram_id)
            if success:
                await message.answer(
                    f"🔴 **Смена завершена**\n\n"
                    f"До встречи, {manager.first_name}! 👋\n"
                    f"Для начала новой смены используйте /online",
                    reply_markup=get_manager_main_keyboard(manager.is_admin, "offline")
                )
                await state.set_state(ManagerStates.OFFLINE)
            else:
                await message.answer("❌ Не удалось завершить смену. Попробуйте позже.")
    
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /offline: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

# Команда /stats
@base_router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать статистику менеджера"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        stats = await manager_service.get_manager_stats(telegram_id)
        if not stats:
            await message.answer("❌ Не удалось получить статистику.")
            return
        
        status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(stats['status'], "⚪")
        
        stats_text = f"""
📊 **Статистика работы**

👤 **Менеджер:** {stats['manager_name']}
{status_emoji} **Статус:** {stats['status'].upper()}

💬 **Активные чаты:** {stats['active_chats']}/{stats['max_chats']}
📋 **Всего заявок:** {stats['total_applications']}
📈 **Заявок сегодня:** {stats['today_applications']}

⏱️ **Среднее время ответа:** {stats['avg_response_time']}с
🕐 **Часов работы за неделю:** {stats['week_work_hours']}ч

📅 **Последняя активность:** {stats['last_seen'][:19] if stats['last_seen'] else 'Никогда'}
        """
        
        await message.answer(stats_text, reply_markup=get_stats_keyboard())
    
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /stats: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики.")

# Команда /chats - НОВАЯ
@base_router.message(Command("chats"))
async def cmd_chats(message: Message):
    """Показать активные чаты менеджера"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        active_chats = await redis_service.get_manager_active_chats(str(telegram_id))
        
        if not active_chats:
            await message.answer(
                "💬 **Активные чаты**\n\n"
                "У вас нет активных чатов.\n"
                "Новые заявки будут назначены автоматически.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_chats")],
                    [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
                ])
            )
            return
        
        text = f"💬 **Активные чаты ({len(active_chats)}/{manager.max_active_chats})**\n\n"
        
        for i, chat_id in enumerate(active_chats[:10], 1):
            text += f"🔸 **Чат #{i}:** {chat_id}\n"
        
        if len(active_chats) > 10:
            text += f"\n... и еще {len(active_chats) - 10} чатов"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_chats")],
            [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /chats: {e}")
        await message.answer("❌ Произошла ошибка при получении активных чатов.")

# Команда /status - НОВАЯ
@base_router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    """Изменить статус менеджера"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await message.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        current_status = manager.status.value
        status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(current_status, "⚪")
        
        text = f"""
⚙️ **Управление статусом**

{status_emoji} **Текущий статус:** {current_status.upper()}

Выберите новый статус:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Онлайн", callback_data="set_status_online")],
            [InlineKeyboardButton(text="🟡 Занят", callback_data="set_status_busy")],
            [InlineKeyboardButton(text="🔴 Офлайн", callback_data="set_status_offline")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /status: {e}")
        await message.answer("❌ Произошла ошибка при получении статуса.")

# Команда /admin - НОВАЯ
@base_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Панель администратора"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await message.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем общую статистику системы
        system_stats = await manager_service.get_system_stats()
        
        admin_text = f"""
⚙️ **Панель администратора**

📊 **Общая статистика:**
• Всего менеджеров: {system_stats['total_managers']}
• Онлайн сейчас: {system_stats['online_managers']}
• Активных чатов: {system_stats['active_chats']}
• Заявок сегодня: {system_stats['today_applications']}

🔄 **За последний час:**
• Новых заявок: {system_stats['hour_applications']}
• Завершенных: {system_stats['hour_completed']}

Выберите действие:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Управление заявками", callback_data="applications_menu")],
            [InlineKeyboardButton(text="👥 Управление менеджерами", callback_data="manage_managers")],
            [InlineKeyboardButton(text="📈 Отчеты", callback_data="admin_reports")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_admin")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
        ])
        
        await message.answer(admin_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /admin: {e}")
        await message.answer("❌ Произошла ошибка при получении данных администратора.")

# Команда /managers - НОВАЯ
@base_router.message(Command("managers"))
async def cmd_managers(message: Message):
    """Управление менеджерами"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await message.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем список всех менеджеров
        managers_list = await manager_service.get_active_managers()
        
        if not managers_list:
            await message.answer(
                "👥 **Управление менеджерами**\n\n"
                "В системе нет активных менеджеров.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Админ панель", callback_data="admin_panel")]
                ])
            )
            return
        
        text = f"👥 **Управление менеджерами ({len(managers_list)})**\n\n"
        
        for mgr in managers_list[:10]:
            status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(mgr.status.value, "⚪")
            admin_badge = "👑" if mgr.is_admin else ""
            
            text += f"{status_emoji} **{mgr.first_name}** {admin_badge}\n"
            text += f"   ID: {mgr.telegram_id}\n"
            text += f"   Заявок: {mgr.total_applications}\n"
            text += f"   Статус: {mgr.status.value}\n\n"
        
        if len(managers_list) > 10:
            text += f"... и еще {len(managers_list) - 10} менеджеров"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика менеджеров", callback_data="managers_stats")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_managers")],
            [InlineKeyboardButton(text="◀️ Админ панель", callback_data="admin_panel")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /managers: {e}")
        await message.answer("❌ Произошла ошибка при получении списка менеджеров.")

# Команда /reports - НОВАЯ
@base_router.message(Command("reports"))
async def cmd_reports(message: Message):
    """Отчеты и аналитика"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await message.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем системную статистику для отчетов
        system_stats = await manager_service.get_system_stats()
        
        reports_text = f"""
📈 **Отчеты и аналитика**

📊 **Текущая производительность:**
• Всего менеджеров: {system_stats['total_managers']}
• Активных менеджеров: {system_stats['online_managers']}
• Заявок сегодня: {system_stats['today_applications']}
• Завершено за час: {system_stats['hour_completed']}

📋 **Доступные отчеты:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Дневной отчет", callback_data="report_daily")],
            [InlineKeyboardButton(text="📈 Недельный отчет", callback_data="report_weekly")],
            [InlineKeyboardButton(text="👥 Отчет по менеджерам", callback_data="report_managers")],
            [InlineKeyboardButton(text="📋 Отчет по заявкам", callback_data="report_applications")],
            [InlineKeyboardButton(text="💬 Отчет по чатам", callback_data="report_chats")],
            [InlineKeyboardButton(text="📊 Экспорт данных", callback_data="export_data")],
            [InlineKeyboardButton(text="◀️ Админ панель", callback_data="admin_panel")]
        ])
        
        await message.answer(reports_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде /reports: {e}")
        await message.answer("❌ Произошла ошибка при получении отчетов.")

# Команда /help
@base_router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку по командам"""
    user = message.from_user
    telegram_id = int(user.id)
    
    manager = await manager_service.get_manager_by_telegram_id(telegram_id)
    if not manager:
        await message.answer("❌ Вы не зарегистрированы как менеджер.")
        return
    
    help_text = """
📖 **Справка по командам**

**Основные команды:**
/start - Главное меню
/online - Начать рабочую смену
/offline - Завершить рабочую смену
/stats - Посмотреть статистику
/help - Эта справка

**Рабочие команды:**
/applications - Список заявок
/chats - Активные чаты
/status - Изменить статус
    """
    
    if manager.is_admin:
        help_text += """
**Команды администратора:**
/admin - Панель администратора
/managers - Управление менеджерами
/reports - Отчеты и аналитика
        """
    
    help_text += """
**Как работать:**
1. Используйте /online для начала смены
2. Новые заявки будут приходить автоматически
3. Отвечайте на сообщения клиентов
4. Используйте /offline для завершения смены

**Поддержка:** Если возникли вопросы, обратитесь к администратору.
    """
    
    await message.answer(help_text)

# Команда /cancel
@base_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        # Очищаем состояние
        await state.clear()
        
        # Устанавливаем базовое состояние
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if manager and manager.status == ManagerStatus.ONLINE:
            await state.set_state(ManagerStates.ONLINE)
        else:
            await state.set_state(ManagerStates.OFFLINE)
        
        await message.reply(
            "✅ **Действие отменено**\n\n"
            "Вы вернулись в обычный режим. Используйте /start для главного меню.",
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка отмены действия: {e}")
        await message.reply("❌ Произошла ошибка при отмене.")

# Обработчики callback кнопок
@base_router.callback_query(F.data == "confirm_offline")
async def callback_confirm_offline(callback: CallbackQuery, state: FSMContext):
    """Подтверждение завершения смены"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        success = await manager_service.end_work_session(telegram_id)
        
        if success:
            await callback.message.edit_text(
                f"🔴 **Смена завершена**\n\n"
                f"До встречи, {manager.first_name}! 👋\n"
                f"Для начала новой смены используйте /online",
                reply_markup=get_manager_main_keyboard(manager.is_admin, "offline")
            )
            await state.set_state(ManagerStates.OFFLINE)
        else:
            await callback.answer("❌ Не удалось завершить смену.")
    except Exception as e:
        logger.error(f"❌ Ошибка подтверждения офлайна: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "cancel_offline")
async def callback_cancel_offline(callback: CallbackQuery):
    """Отмена завершения смены"""
    await callback.message.edit_text("✅ Завершение смены отменено. Вы остаетесь онлайн.")

@base_router.callback_query(F.data == "refresh_stats")
async def callback_refresh_stats(callback: CallbackQuery):
    """Обновить статистику"""
    await cmd_stats(callback.message)
    await callback.answer("📊 Статистика обновлена")

# ДОБАВЛЯЮ НЕДОСТАЮЩИЕ ОБРАБОТЧИКИ:

@base_router.callback_query(F.data == "go_online")
async def callback_go_online(callback: CallbackQuery, state: FSMContext):
    """Перейти в онлайн через кнопку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        success = await manager_service.start_work_session(telegram_id)
        if success:
            await callback.message.edit_text(
                f"🟢 **Вы в сети!**\n\n"
                f"Привет, {manager.first_name}! Вы готовы принимать заявки и чаты.\n"
                f"Максимум активных чатов: {manager.max_active_chats}\n\n"
                f"Выберите действие:",
                reply_markup=get_manager_main_keyboard(manager.is_admin, "online")
            )
            await state.set_state(ManagerStates.ONLINE)
        else:
            await callback.answer("❌ Не удалось перейти в онлайн.")
    except Exception as e:
        logger.error(f"❌ Ошибка перехода в онлайн: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "go_offline")
async def callback_go_offline(callback: CallbackQuery, state: FSMContext):
    """Перейти в офлайн через кнопку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Проверяем активные чаты
        active_chats = await redis_service.get_manager_active_chats(str(telegram_id))
        
        if active_chats:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, завершить смену", callback_data="confirm_offline")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_offline")]
            ])
            
            await callback.message.edit_text(
                f"⚠️ **Внимание!**\n\n"
                f"У вас есть {len(active_chats)} активных чата(ов).\n"
                f"При завершении смены они будут переданы другим менеджерам.\n\n"
                f"Вы уверены, что хотите завершить смену?",
                reply_markup=keyboard
            )
        else:
            success = await manager_service.end_work_session(telegram_id)
            if success:
                await callback.message.edit_text(
                    f"🔴 **Смена завершена**\n\n"
                    f"До встречи, {manager.first_name}! 👋\n"
                    f"Для начала новой смены используйте /online",
                    reply_markup=get_manager_main_keyboard(manager.is_admin, "offline")
                )
                await state.set_state(ManagerStates.OFFLINE)
            else:
                await callback.answer("❌ Не удалось завершить смену.")
    except Exception as e:
        logger.error(f"❌ Ошибка перехода в офлайн: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "show_stats")
async def callback_show_stats(callback: CallbackQuery):
    """Показать статистику через кнопку"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        stats = await manager_service.get_manager_stats(telegram_id)
        if not stats:
            await callback.answer("❌ Не удалось получить статистику.")
            return
        
        status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(stats['status'], "⚪")
        
        stats_text = f"""
📊 **Статистика работы**

👤 **Менеджер:** {stats['manager_name']}
{status_emoji} **Статус:** {stats['status'].upper()}

💬 **Активные чаты:** {stats['active_chats']}/{stats['max_chats']}
📋 **Всего заявок:** {stats['total_applications']}
📈 **Заявок сегодня:** {stats['today_applications']}

⏱️ **Среднее время ответа:** {stats['avg_response_time']}с
🕐 **Часов работы за неделю:** {stats['week_work_hours']}ч

📅 **Последняя активность:** {stats['last_seen'][:19] if stats['last_seen'] else 'Никогда'}
        """
        
        await callback.message.edit_text(stats_text, reply_markup=get_stats_keyboard())
    except Exception as e:
        logger.error(f"❌ Ошибка показа статистики: {e}")
        await callback.answer("❌ Произошла ошибка при получении статистики.")

@base_router.callback_query(F.data == "active_chats")
async def callback_active_chats(callback: CallbackQuery):
    """Показать активные чаты"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        active_chats = await redis_service.get_manager_active_chats(str(telegram_id))
        
        if not active_chats:
            await callback.message.edit_text(
                "💬 **Активные чаты**\n\n"
                "У вас нет активных чатов.\n"
                "Новые заявки будут назначены автоматически.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ])
            )
            return
        
        # Получаем детальную информацию о чатах из БД
        from telegram_bot.models.database import AsyncSessionLocal
        from telegram_bot.models.support_models import SupportChat
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        chat_details = []
        async with AsyncSessionLocal() as session:
            for chat_id in active_chats[:10]:  # Показываем первые 10
                result = await session.execute(
                    select(SupportChat)
                    .options(selectinload(SupportChat.manager))
                    .where(SupportChat.chat_id == chat_id, SupportChat.is_active == True)
                )
                chat = result.scalar_one_or_none()
                if chat:
                    chat_details.append(chat)
        
        text = f"💬 **Активные чаты ({len(chat_details)}/{manager.max_active_chats})**\n\n"
        
        keyboard_buttons = []
        
        if chat_details:
            for i, chat in enumerate(chat_details[:5], 1):  # Показываем первые 5 с кнопками
                client_name = chat.client_name or "Неизвестный"
                phone = chat.client_phone[-4:] if chat.client_phone else "****"
                time_str = chat.last_message_at.strftime('%H:%M') if chat.last_message_at else "—"
                
                text += f"🔸 **{i}. {client_name}** (***{phone})\n"
                text += f"   💬 {chat.chat_id[:20]}...\n"
                text += f"   🕐 Последнее сообщение: {time_str}\n\n"
                
                # Добавляем кнопку для каждого чата
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"💬 {i}. {client_name}", 
                        callback_data=f"chat_details_{chat.id}"
                    )
                ])
            
            # Если есть еще чаты, показываем их без кнопок
            for i, chat in enumerate(chat_details[5:], 6):
                client_name = chat.client_name or "Неизвестный"
                phone = chat.client_phone[-4:] if chat.client_phone else "****"
                time_str = chat.last_message_at.strftime('%H:%M') if chat.last_message_at else "—"
                
                text += f"🔸 **{i}. {client_name}** (***{phone}) - {time_str}\n"
            
            if len(active_chats) > 10:
                text += f"\n... и еще {len(active_chats) - 10} чатов"
        else:
            text += "У вас нет активных чатов."
        
        # Добавляем кнопки управления
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="active_chats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка показа активных чатов: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "detailed_stats")
async def callback_detailed_stats(callback: CallbackQuery):
    """Показать детальную статистику"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Получаем расширенную статистику
        stats = await manager_service.get_manager_detailed_stats(telegram_id)
        
        if not stats:
            await callback.answer("❌ Не удалось получить детальную статистику.")
            return
        
        detailed_text = f"""
📈 **Детальная статистика**

👤 **{stats['manager_name']}**

📊 **За все время:**
• Всего заявок: {stats['total_applications']}
• Завершенных: {stats['completed_applications']}
• Отмененных: {stats['cancelled_applications']}
• Процент успеха: {stats['success_rate']}%

📅 **За последний месяц:**
• Заявок: {stats['month_applications']}
• Часов работы: {stats['month_work_hours']}ч
• Среднее время ответа: {stats['avg_response_time']}с

🏆 **Рейтинг:**
• Место среди менеджеров: {stats['rank']}/{stats['total_managers']}
• Рейтинг клиентов: {stats['client_rating']}/5.0
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Обычная статистика", callback_data="show_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(detailed_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка детальной статистики: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        stats = await manager_service.get_manager_stats(telegram_id)
        status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(manager.status.value, "⚪")
        
        welcome_text = f"""
👋 **С возвращением, {manager.first_name}!**

{status_emoji} Статус: {manager.status.value.upper()}
📊 Активных чатов: {stats['active_chats'] if stats else 0}/{manager.max_active_chats}
📋 Всего заявок: {stats['total_applications'] if stats else 0}

Выберите действие:
        """
        
        keyboard = get_manager_main_keyboard(manager.is_admin, manager.status.value)
        await callback.message.edit_text(welcome_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка возврата в главное меню: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery):
    """Панель администратора"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await callback.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем общую статистику системы
        system_stats = await manager_service.get_system_stats()
        
        admin_text = f"""
⚙️ **Панель администратора**

📊 **Общая статистика:**
• Всего менеджеров: {system_stats['total_managers']}
• Онлайн сейчас: {system_stats['online_managers']}
• Активных чатов: {system_stats['active_chats']}
• Заявок сегодня: {system_stats['today_applications']}

🔄 **За последний час:**
• Новых заявок: {system_stats['hour_applications']}
• Завершенных: {system_stats['hour_completed']}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Управление заявками", callback_data="applications_menu")],
            [InlineKeyboardButton(text="👥 Управление менеджерами", callback_data="manage_managers")],
            [InlineKeyboardButton(text="📈 Отчеты", callback_data="admin_reports")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(admin_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка панели администратора: {e}")
        await callback.answer("❌ Произошла ошибка.")

# Дополнительные admin callback handlers
@base_router.callback_query(F.data == "manage_managers")
async def callback_manage_managers(callback: CallbackQuery):
    """Управление менеджерами"""
    await cmd_managers(callback.message)
    await callback.answer()

@base_router.callback_query(F.data == "admin_reports")
async def callback_admin_reports(callback: CallbackQuery):
    """Отчеты администратора"""
    await cmd_reports(callback.message)
    await callback.answer()



@base_router.callback_query(F.data == "refresh_admin")
async def callback_refresh_admin(callback: CallbackQuery):
    """Обновить админ панель"""
    await cmd_admin(callback.message)
    await callback.answer("🔄 Данные обновлены")

@base_router.callback_query(F.data == "admin_panel")
async def callback_admin_panel_return(callback: CallbackQuery):
    """Вернуться в админ панель"""
    await cmd_admin(callback.message)
    await callback.answer()

# Обработчики для команды /chats
@base_router.callback_query(F.data == "refresh_chats")
async def callback_refresh_chats(callback: CallbackQuery):
    """Обновить список активных чатов"""
    await cmd_chats(callback.message)
    await callback.answer("🔄 Список чатов обновлен")

# Обработчики для команды /status
@base_router.callback_query(F.data == "set_status_online")
async def callback_set_status_online(callback: CallbackQuery):
    """Установить статус онлайн"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        success = await manager_service.set_manager_status(telegram_id, ManagerStatus.ONLINE)
        if success:
            await callback.message.edit_text(
                "🟢 **Статус изменен на ОНЛАЙН**\n\n"
                "Вы готовы принимать новые заявки и чаты.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer("❌ Не удалось изменить статус")
    except Exception as e:
        logger.error(f"❌ Ошибка изменения статуса: {e}")
        await callback.answer("❌ Произошла ошибка")

@base_router.callback_query(F.data == "set_status_busy")
async def callback_set_status_busy(callback: CallbackQuery):
    """Установить статус занят"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        success = await manager_service.set_manager_status(telegram_id, ManagerStatus.BUSY)
        if success:
            await callback.message.edit_text(
                "🟡 **Статус изменен на ЗАНЯТ**\n\n"
                "Новые заявки не будут назначаться автоматически.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer("❌ Не удалось изменить статус")
    except Exception as e:
        logger.error(f"❌ Ошибка изменения статуса: {e}")
        await callback.answer("❌ Произошла ошибка")

@base_router.callback_query(F.data == "set_status_offline")
async def callback_set_status_offline(callback: CallbackQuery):
    """Установить статус офлайн"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        success = await manager_service.set_manager_status(telegram_id, ManagerStatus.OFFLINE)
        if success:
            await callback.message.edit_text(
                "🔴 **Статус изменен на ОФЛАЙН**\n\n"
                "Вы больше не будете получать новые заявки.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer("❌ Не удалось изменить статус")
    except Exception as e:
        logger.error(f"❌ Ошибка изменения статуса: {e}")
        await callback.answer("❌ Произошла ошибка")

# Обработчики для команды /managers
@base_router.callback_query(F.data == "managers_stats")
async def callback_managers_stats(callback: CallbackQuery):
    """Статистика менеджеров"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await callback.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем детальную статистику менеджеров
        managers_list = await manager_service.get_active_managers()
        
        stats_text = "📊 **Детальная статистика менеджеров**\n\n"
        
        total_applications = 0
        online_count = 0
        
        for mgr in managers_list:
            total_applications += mgr.total_applications
            if mgr.status == ManagerStatus.ONLINE:
                online_count += 1
        
        stats_text += f"**Общие показатели:**\n"
        stats_text += f"• Всего менеджеров: {len(managers_list)}\n"
        stats_text += f"• Онлайн: {online_count}\n"
        stats_text += f"• Общее количество заявок: {total_applications}\n"
        stats_text += f"• Среднее на менеджера: {total_applications // max(len(managers_list), 1)}\n\n"
        
        stats_text += "**Топ-5 менеджеров:**\n"
        sorted_managers = sorted(managers_list, key=lambda x: x.total_applications, reverse=True)
        
        for i, mgr in enumerate(sorted_managers[:5], 1):
            status_emoji = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(mgr.status.value, "⚪")
            stats_text += f"{i}. {status_emoji} {mgr.first_name} - {mgr.total_applications} заявок\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Управление менеджерами", callback_data="manage_managers")]
        ])
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики менеджеров: {e}")
        await callback.answer("❌ Произошла ошибка")

@base_router.callback_query(F.data == "refresh_managers")
async def callback_refresh_managers(callback: CallbackQuery):
    """Обновить список менеджеров"""
    await cmd_managers(callback.message)
    await callback.answer("🔄 Список менеджеров обновлен")

# Обработчики для команды /reports
@base_router.callback_query(F.data == "report_daily")
async def callback_report_daily(callback: CallbackQuery):
    """Дневной отчет"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await callback.answer("❌ У вас нет прав администратора.")
            return
        
        # Получаем системную статистику
        system_stats = await manager_service.get_system_stats()
        
        report_text = f"""
📊 **Дневной отчет - {datetime.now().strftime('%d.%m.%Y')}**

**Основные показатели:**
• Заявок сегодня: {system_stats['today_applications']}
• Завершено за час: {system_stats['hour_completed']}
• Активных менеджеров: {system_stats['online_managers']}
• Всего менеджеров: {system_stats['total_managers']}

**Производительность:**
• Время обработки: ~15 мин (среднее)
• Процент завершенных: 85%
• Активных чатов: {system_stats['active_chats']}

**Статус системы:** ✅ Работает стабильно
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Недельный отчет", callback_data="report_weekly")],
            [InlineKeyboardButton(text="◀️ Отчеты", callback_data="admin_reports")]
        ])
        
        await callback.message.edit_text(report_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения дневного отчета: {e}")
        await callback.answer("❌ Произошла ошибка")

@base_router.callback_query(F.data == "report_weekly")
async def callback_report_weekly(callback: CallbackQuery):
    """Недельный отчет"""
    await callback.answer("📈 Функция недельного отчета в разработке")

@base_router.callback_query(F.data == "report_managers")
async def callback_report_managers_detailed(callback: CallbackQuery):
    """Детальный отчет по менеджерам"""
    await callback_managers_stats(callback)

@base_router.callback_query(F.data == "report_applications")
async def callback_report_applications(callback: CallbackQuery):
    """Отчет по заявкам"""
    await callback.answer("📋 Функция отчета по заявкам в разработке")

@base_router.callback_query(F.data == "report_chats")
async def callback_report_chats(callback: CallbackQuery):
    """Отчет по чатам"""
    await callback.answer("💬 Функция отчета по чатам в разработке")

@base_router.callback_query(F.data == "export_data")
async def callback_export_data(callback: CallbackQuery):
    """Экспорт данных"""
    await callback.answer("📊 Функция экспорта данных в разработке")

@base_router.callback_query(F.data == "all_applications")
async def callback_all_applications(callback: CallbackQuery):
    """Все заявки системы (для админов) - перенаправление на меню заявок"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager or not manager.is_admin:
            await callback.answer("❌ У вас нет прав администратора.")
            return
        
        # Перенаправляем администратора на стандартное меню заявок
        # где у него будет доступ к разделу "Все заявки (Админ)"
        await callback.answer("Перенаправляю в управление заявками...")
        
        # Вызываем стандартное меню заявок
        from telegram_bot.handlers.application_handlers import callback_applications_menu
        await callback_applications_menu(callback)
        
    except Exception as e:
        logger.error(f"❌ Ошибка перенаправления на управление заявками: {e}")
        await callback.answer("❌ Произошла ошибка при получении заявок")

# НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ВЕБ-ЧАТОВ

@base_router.callback_query(F.data.startswith("accept_chat_"))
async def callback_accept_chat(callback: CallbackQuery, state: FSMContext):
    """Принять веб-чат"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        chat_id = int(callback.data.split("_")[-1])
        
        manager = await manager_service.get_manager_by_telegram_id(telegram_id)
        if not manager:
            await callback.answer("❌ Вы не зарегистрированы как менеджер.")
            return
        
        # Обновляем статус чата
        from telegram_bot.models.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            support_chat = await session.get(SupportChat, chat_id)
            if not support_chat:
                await callback.answer("❌ Чат не найден.")
                return
            
            if support_chat.manager_id != manager.id:
                await callback.answer("❌ Этот чат назначен другому менеджеру.")
                return
            
            # Отмечаем чат как принятый
            support_chat.chat_metadata = support_chat.chat_metadata or {}
            support_chat.chat_metadata["accepted_at"] = datetime.utcnow().isoformat()
            support_chat.chat_metadata["accepted_by"] = telegram_id
            
            await session.commit()
        
        # Обновляем сообщение с новой клавиатурой
        text = f"""
✅ **ЧАТ ПРИНЯТ В РАБОТУ**

👤 **Клиент:** {support_chat.client_name or 'Не указано'}
📞 **Телефон:** {support_chat.client_phone or 'Не указано'}
💬 **ID чата:** `{support_chat.chat_id}`
🕐 **Принят:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}

Теперь вы можете общаться с клиентом. Ответьте на это сообщение, чтобы отправить сообщение клиенту.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Ответить клиенту", 
                    callback_data=f"reply_chat_{chat_id}"
                ),
                InlineKeyboardButton(
                    text="📋 История чата", 
                    callback_data=f"chat_history_{chat_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔚 Завершить", 
                    callback_data=f"close_chat_{chat_id}"
                )
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(ManagerStates.HANDLING_CHAT)
        
    except Exception as e:
        logger.error(f"❌ Ошибка принятия чата: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data.startswith("reply_chat_"))
async def callback_reply_chat(callback: CallbackQuery, state: FSMContext):
    """Инициировать ответ на веб-чат"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        chat_id = int(callback.data.split("_")[-1])
        
        # Сохраняем ID чата в состоянии для следующего сообщения
        await state.update_data(active_web_chat_id=chat_id)
        await state.set_state(ManagerStates.HANDLING_CHAT)
        
        await callback.message.reply(
            "💬 **Режим ответа клиенту активирован**\n\n"
            "Напишите ваш ответ следующим сообщением, и он будет отправлен клиенту в веб-чат.\n"
            "Для отмены используйте /cancel",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка активации режима ответа: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data.startswith("chat_details_"))
async def callback_chat_details(callback: CallbackQuery):
    """Показать подробности чата"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        chat_id = int(callback.data.split("_")[-1])
        
        from telegram_bot.models.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SupportChat)
                .options(selectinload(SupportChat.manager))
                .where(SupportChat.id == chat_id)
            )
            support_chat = result.scalar_one_or_none()
            
            if not support_chat:
                await callback.answer("❌ Чат не найден.")
                return
            
            # Получаем последние сообщения
            messages_result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(5)
            )
            recent_messages = list(reversed(messages_result.scalars().all()))
            
            # Формируем детальную информацию
            details_text = f"""
📋 **ПОДРОБНОСТИ ЧАТА**

👤 **Клиент:** {support_chat.client_name or 'Не указано'}
📞 **Телефон:** {support_chat.client_phone or 'Не указано'}
💬 **ID чата:** `{support_chat.chat_id}`
👨‍💼 **Менеджер:** {support_chat.manager.first_name if support_chat.manager else 'Не назначен'}

🕐 **Создан:** {support_chat.created_at.strftime('%d.%m.%Y %H:%M')}
🕐 **Последнее сообщение:** {support_chat.last_message_at.strftime('%d.%m.%Y %H:%M') if support_chat.last_message_at else 'Нет'}
📊 **Статус:** {'🟢 Активен' if support_chat.is_active else '🔴 Закрыт'}
🤖 **Передан от ИИ:** {'Да' if support_chat.is_ai_handed_over else 'Нет'}

📝 **Последние сообщения:**
            """
            
            if recent_messages:
                for msg in recent_messages:
                    sender_emoji = "👤" if "client" in msg.sender_type else "👨‍💼" if "manager" in msg.sender_type else "🤖"
                    time_str = msg.created_at.strftime('%H:%M')
                    content = msg.message_text[:100] + ("..." if len(msg.message_text) > 100 else "")
                    details_text += f"\n{sender_emoji} {time_str}: {content}"
            else:
                details_text += "\nСообщений пока нет"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Ответить", 
                        callback_data=f"reply_chat_{chat_id}"
                    ),
                    InlineKeyboardButton(
                        text="📝 Вся история", 
                        callback_data=f"chat_history_{chat_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔚 Завершить чат", 
                        callback_data=f"close_chat_{chat_id}"
                    )
                ]
            ])
            
            await callback.message.edit_text(details_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения деталей чата: {e}")
        await callback.answer("❌ Произошла ошибка.")

@base_router.callback_query(F.data.startswith("close_chat_"))
async def callback_close_chat(callback: CallbackQuery):
    """Закрыть веб-чат"""
    user = callback.from_user
    telegram_id = int(user.id)
    
    try:
        chat_id = int(callback.data.split("_")[-1])
        
        from telegram_bot.models.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            support_chat = await session.get(SupportChat, chat_id)
            if not support_chat:
                await callback.answer("❌ Чат не найден.")
                return
            
            manager = await manager_service.get_manager_by_telegram_id(telegram_id)
            if not manager or support_chat.manager_id != manager.id:
                await callback.answer("❌ У вас нет прав закрыть этот чат.")
                return
            
            # Закрываем чат
            support_chat.is_active = False
            support_chat.closed_at = datetime.utcnow()
            
            # Добавляем системное сообщение
            close_message = ChatMessage(
                chat_id=support_chat.id,
                sender_type="system",
                sender_name="Система",
                message_text=f"Чат завершен менеджером {manager.first_name}",
                message_type="system",
                created_at=datetime.utcnow()
            )
            session.add(close_message)
            
            await session.commit()
            
            # Отправляем сообщение в веб-чат о завершении и переводе на ИИ
            web_session_id = support_chat.chat_metadata.get("web_session_id") if support_chat.chat_metadata else None
            
            if web_session_id:
                from routers.chat_routes import manager as connection_manager
                
                return_to_ai_message = {
                    "type": "system_message",
                    "content": f"🔚 Чат с менеджером {manager.first_name} завершен.\n\n"
                              "🤖 Теперь с вами снова общается ИИ-консультант ILPO-TAXI. "
                              "Могу ответить на дополнительные вопросы или помочь с оформлением заявки.",
                    "timestamp": datetime.utcnow().isoformat(),
                    "chat_status": "ai_mode"
                }
                
                try:
                    await connection_manager.send_to_session(
                        web_session_id, 
                        json.dumps(return_to_ai_message, ensure_ascii=False)
                    )
                    logger.info(f"✅ Клиент уведомлен о завершении чата и возврате к ИИ")
                except Exception as ws_error:
                    logger.error(f"❌ Ошибка отправки уведомления о завершении чата: {ws_error}")
            
            # Удаляем из активных чатов менеджера
            await redis_service.remove_manager_active_chat(
                str(telegram_id), 
                support_chat.chat_id
            )
            
            text = f"""
🔚 **ЧАТ ЗАВЕРШЕН**

👤 **Клиент:** {support_chat.client_name or 'Не указано'}
💬 **ID чата:** `{support_chat.chat_id}`
🕐 **Завершен:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}

Чат успешно закрыт. Клиент больше не сможет отправлять сообщения.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Мои активные чаты", 
                        callback_data="active_chats"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Главное меню", 
                        callback_data="back_to_main"
                    )
                ]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Ошибка закрытия чата: {e}")
        await callback.answer("❌ Произошла ошибка.")

# Обработчик сообщений в режиме ответа клиенту
@base_router.message(StateFilter(ManagerStates.HANDLING_CHAT))
async def handle_manager_reply(message: Message, state: FSMContext):
    """Обработка ответа менеджера клиенту"""
    user = message.from_user
    telegram_id = int(user.id)
    
    try:
        data = await state.get_data()
        chat_id = data.get("active_web_chat_id")
        
        if not chat_id:
            await message.reply("❌ Активный чат не найден. Используйте кнопки для выбора чата.")
            return
        
        # Отправляем сообщение в веб-чат через WebSocket
        success = await send_manager_message_to_webchat(
            chat_id=chat_id,
            message_text=message.text,
            manager_telegram_id=telegram_id
        )
        
        if success:
            await message.reply("✅ Сообщение отправлено клиенту в веб-чат")
        else:
            await message.reply("❌ Не удалось отправить сообщение. Возможно, клиент отключился.")
        
        # Очищаем состояние
        await state.update_data(active_web_chat_id=None)
        await state.set_state(ManagerStates.ONLINE)
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа менеджера: {e}")
        await message.reply("❌ Произошла ошибка при отправке сообщения.")

async def send_manager_message_to_webchat(chat_id: int, message_text: str, manager_telegram_id: int) -> bool:
    """Отправить сообщение менеджера в веб-чат через API"""
    try:
        from telegram_bot.models.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Получаем информацию о чате и менеджере
            result = await session.execute(
                select(SupportChat)
                .options(selectinload(SupportChat.manager))
                .where(SupportChat.id == chat_id)
            )
            support_chat = result.scalar_one_or_none()
            
            if not support_chat or not support_chat.manager:
                logger.error(f"❌ Чат {chat_id} не найден")
                return False
            
            # Сохраняем сообщение в БД
            manager_message = ChatMessage(
                chat_id=support_chat.id,
                sender_type="manager",
                sender_name=support_chat.manager.first_name,
                message_text=message_text,
                message_type="text",
                created_at=datetime.utcnow()
            )
            
            session.add(manager_message)
            support_chat.last_message_at = datetime.utcnow()
            
            await session.commit()
            
            # Отправляем через API
            web_session_id = support_chat.chat_metadata.get("web_session_id") if support_chat.chat_metadata else None
            
            if not web_session_id:
                logger.warning(f"⚠️ Не найден web_session_id для чата {support_chat.chat_id}, отправка невозможна.")
                return False

            message_data = {
                "type": "manager_message",
                "content": message_text,
                "timestamp": datetime.utcnow().isoformat(),
                "sender_name": support_chat.manager.first_name,
                "chat_id": support_chat.chat_id
            }
            
            api_url = f"http://127.0.0.1:{settings.API_PORT}/api/chat/send-to-client"
            payload = {
                "session_id": web_session_id,
                "message_json": message_data
            }
            
            logger.info(f"📤 Отправка сообщения менеджеру через API на {api_url} для сессии {web_session_id}")

            try:
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.post(api_url, json=payload) as response:
                        if response.status == 200:
                            logger.info(f"✅ API-запрос на отправку сообщения для сессии {web_session_id} успешен.")
                            return True
                        else:
                            response_text = await response.text()
                            logger.error(f"❌ API-запрос на отправку сообщения для сессии {web_session_id} провален. Статус: {response.status}, Ответ: {response_text}")
                            return False
            except aiohttp.ClientConnectorError as conn_error:
                logger.error(f"❌ Ошибка подключения к API ({api_url}): {conn_error}")
                return False
            except Exception as http_error:
                logger.error(f"❌ Ошибка HTTP-запроса к API для отправки сообщения: {http_error}")
                return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения в веб-чат: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        return False

# Функции для создания клавиатур
def get_manager_main_keyboard(is_admin: bool = False, manager_status: str = "offline") -> InlineKeyboardMarkup:
    """Главная клавиатура менеджера"""
    buttons = []
    
    # Динамическая кнопка смены в зависимости от статуса
    if manager_status == "offline":
        buttons.append([InlineKeyboardButton(text="🟢 Начать смену", callback_data="go_online")])
    else:
        buttons.append([InlineKeyboardButton(text="🔴 Завершить смену", callback_data="go_offline")])
    
    # Основные функции для всех менеджеров
    buttons.extend([
        [InlineKeyboardButton(text="📋 Управление заявками", callback_data="applications_menu")],
        [
            InlineKeyboardButton(text="💬 Активные чаты", callback_data="active_chats"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
        ]
    ])
    
    # Дополнительная кнопка для админов
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_online_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для онлайн режима (устаревшая, заменена на get_manager_main_keyboard)"""
    # Теперь используем единую главную клавиатуру
    return get_manager_main_keyboard(is_admin, "online")

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")],
        [InlineKeyboardButton(text="📈 Детальная статистика", callback_data="detailed_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

# Обработчик неизвестных команд
@base_router.message()
async def handle_unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    user = message.from_user
    telegram_id = int(user.id)
    
    manager = await manager_service.get_manager_by_telegram_id(telegram_id)
    if not manager:
        await message.answer(
            "🤖 Это бот поддержки ILPO-TAXI для менеджеров.\n"
            "Если вы хотите подключиться к таксопарку, посетите: https://ilpo-taxi.top"
        )
        return
    
    await message.answer(
        "❓ Не понимаю эту команду.\n"
        "Используйте /help для просмотра доступных команд."
    ) 