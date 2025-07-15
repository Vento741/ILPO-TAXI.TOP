"""
Основной файл Telegram бота поддержки ILPO-TAXI
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from telegram_bot.config.settings import settings, validate_settings
from telegram_bot.models.database import init_db, close_db
from telegram_bot.services.redis_service import redis_service
from telegram_bot.handlers.base_handlers import base_router
from telegram_bot.handlers.application_handlers import application_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot: Bot = None
dp: Dispatcher = None

async def create_bot() -> Bot:
    """Создание экземпляра бота"""
    global bot
    
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    logger.info("✅ Бот создан успешно")
    return bot

async def create_dispatcher() -> Dispatcher:
    """Создание диспетчера с Redis storage"""
    global dp
    
    # Создаем Redis storage для FSM
    storage = RedisStorage.from_url(settings.REDIS_URL)
    
    # Создаем диспетчер
    dp = Dispatcher(storage=storage)
    
    logger.info("✅ Диспетчер создан")
    return dp

async def setup_routers():
    """Настройка роутеров"""
    global dp
    
    if dp is None:
        logger.error("❌ Диспетчер не инициализирован!")
        return
    
    # Подключаем роутеры
    logger.info("📋 Подключение роутеров...")
    dp.include_router(base_router)
    logger.info("✅ Base router подключен")
    dp.include_router(application_router)
    logger.info("✅ Application router подключен")
    
    # Показываем зарегистрированные обработчики  
    try:
        handler_count = len(dp.message.handlers) if hasattr(dp, 'message') else "неизвестно"
        logger.info(f"📊 Всего обработчиков в диспетчере: {handler_count}")
    except Exception as e:
        logger.info(f"📊 Не удалось подсчитать обработчики: {e}")
    
    logger.info("✅ Роутеры настроены")

async def on_startup():
    """Действия при запуске бота"""
    try:
        logger.info("🚀 Запуск Telegram бота поддержки ILPO-TAXI...")
        
        # Проверяем настройки
        validate_settings()
        logger.info("✅ Настройки проверены")
        
        # Инициализируем базу данных
        await init_db()
        logger.info("✅ База данных инициализирована")
        
        # Подключаемся к Redis
        await redis_service.connect()
        logger.info("✅ Redis подключен")
        
        # Настраиваем роутеры
        await setup_routers()
        
        # Устанавливаем команды бота
        await set_bot_commands()
        
        # Отправляем уведомление админам о запуске
        await notify_admins_startup()
        
        logger.info("🎉 Бот успешно запущен и готов к работе!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise

async def on_shutdown():
    """Действия при завершении работы бота"""
    try:
        logger.info("🛑 Завершение работы бота...")
        
        # Отправляем уведомление админам о завершении
        await notify_admins_shutdown()
        
        # Закрываем соединения
        await redis_service.disconnect()
        await close_db()
        
        logger.info("✅ Бот корректно завершил работу")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при завершении работы бота: {e}")

async def set_bot_commands():
    """Установка команд бота"""
    from aiogram.types import BotCommand
    
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="online", description="🟢 Начать рабочую смену"),
        BotCommand(command="offline", description="🔴 Завершить рабочую смену"),
        BotCommand(command="stats", description="📊 Статистика работы"),
        BotCommand(command="applications", description="📋 Мои заявки"),
        BotCommand(command="chats", description="💬 Активные чаты"),
        BotCommand(command="status", description="⚙️ Изменить статус"),
        BotCommand(command="admin", description="👑 Панель администратора"),
        BotCommand(command="managers", description="👥 Управление менеджерами"),
        BotCommand(command="reports", description="📈 Отчеты и аналитика"),
        BotCommand(command="help", description="❓ Справка по командам"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("✅ Команды бота установлены")
    
    # Проверяем, какие команды установлены
    installed_commands = await bot.get_my_commands()
    logger.info(f"📋 Установленные команды: {[cmd.command for cmd in installed_commands]}")

async def notify_admins_startup():
    """Уведомление админов о запуске бота"""
    if not settings.ADMIN_IDS:
        return
    
    startup_message = """
🚀 **Бот поддержки ILPO-TAXI запущен!**

✅ Все системы работают нормально
📊 База данных: подключена
🔄 Redis: подключен
🌐 API: готов к работе

Менеджеры могут начинать работу.
    """
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=startup_message)
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")

async def notify_admins_shutdown():
    """Уведомление админов о завершении работы бота"""
    if not settings.ADMIN_IDS:
        return
    
    shutdown_message = """
🛑 **Бот поддержки ILPO-TAXI завершает работу**

Все активные сессии будут сохранены.
Перезапуск будет выполнен автоматически.
    """
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=shutdown_message)
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем бота и диспетчер
        await create_bot()
        await create_dispatcher()
        
        # Регистрируем startup и shutdown callbacks
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запускаем поллинг
        logger.info("▶️ Запуск поллинга...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        # Финальная очистка
        if bot:
            await bot.session.close()

def run_bot():
    """Запуск бота с обработкой исключений"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_bot() 