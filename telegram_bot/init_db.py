#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""
import asyncio
import logging
from telegram_bot.models.database import init_db, engine
from telegram_bot.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Инициализация базы данных"""
    try:
        logger.info("🚀 Начинаем инициализацию базы данных...")
        logger.info(f"📊 Подключение к БД: {settings.DATABASE_URL}")
        
        # Проверяем подключение
        async with engine.begin() as conn:
            result = await conn.execute("SELECT version()")
            version = result.fetchone()
            logger.info(f"✅ Подключение к PostgreSQL успешно: {version[0]}")
        
        # Создаем таблицы
        await init_db()
        logger.info("✅ Таблицы базы данных созданы успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        logger.error(f"Подробности: {traceback.format_exc()}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main()) 