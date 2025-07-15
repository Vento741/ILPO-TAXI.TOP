"""
Базовые обработчики команд Telegram бота поддержки ILPO-TAXI
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from telegram_bot.services.manager_service import manager_service
from telegram_bot.services.redis_service import redis_service
from telegram_bot.models.support_models import ManagerStatus, ApplicationStatus
from telegram_bot.config.settings import settings

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
                
                await message.answer(welcome_text, reply_markup=get_manager_main_keyboard(is_admin))
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
            
            await message.answer(welcome_text, reply_markup=get_manager_main_keyboard(manager.is_admin))
            
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
                reply_markup=get_online_keyboard(manager.is_admin)
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
                    reply_markup=get_manager_main_keyboard(manager.is_admin)
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
                reply_markup=get_manager_main_keyboard(manager.is_admin)
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
                reply_markup=get_online_keyboard(manager.is_admin)
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
                    reply_markup=get_manager_main_keyboard(manager.is_admin)
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
        
        text = f"💬 **Активные чаты ({len(active_chats)}/{manager.max_active_chats})**\n\n"
        
        for chat_id in active_chats[:5]:  # Показываем первые 5
            # Здесь можно добавить информацию о чате из Redis
            text += f"🔸 Чат #{chat_id}\n"
        
        if len(active_chats) > 5:
            text += f"\n... и еще {len(active_chats) - 5} чатов"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="active_chats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
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
        
        keyboard = get_manager_main_keyboard(manager.is_admin) if manager.status.value == "offline" else get_online_keyboard(manager.is_admin)
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
            [InlineKeyboardButton(text="👥 Управление менеджерами", callback_data="manage_managers")],
            [InlineKeyboardButton(text="📈 Отчеты", callback_data="admin_reports")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
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
    await callback.answer("🚧 Раздел в разработке")

@base_router.callback_query(F.data == "admin_reports")
async def callback_admin_reports(callback: CallbackQuery):
    """Отчеты администратора"""
    await callback.answer("🚧 Раздел в разработке")

@base_router.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: CallbackQuery):
    """Настройки администратора"""
    await callback.answer("🚧 Раздел в разработке")

# Функции для создания клавиатур
def get_manager_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главная клавиатура менеджера"""
    buttons = [
        [InlineKeyboardButton(text="🟢 Начать смену", callback_data="go_online")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_applications")],
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_online_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для онлайн режима"""
    buttons = [
        [InlineKeyboardButton(text="📋 Новые заявки", callback_data="new_applications")],
        [InlineKeyboardButton(text="💬 Активные чаты", callback_data="active_chats")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="🔴 Завершить смену", callback_data="go_offline")],
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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