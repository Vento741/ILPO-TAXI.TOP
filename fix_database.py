#!/usr/bin/env python3
"""
Скрипт для исправления схемы базы данных
Исправляет проблему с полем updated_at в таблице applications
"""

import asyncio
import sys
import os

# Добавляем путь к telegram_bot в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'telegram_bot'))

from telegram_bot.models.database import engine, Base, AsyncSessionLocal
from telegram_bot.models.support_models import Application, Manager
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_database():
    """Исправить схему базы данных"""
    try:
        logger.info("🔧 Начинаем исправление схемы базы данных...")
        
        async with engine.begin() as conn:
            # Пересоздаем таблицы
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("🗑️ Старые таблицы удалены")
            
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Новые таблицы созданы с исправленной схемой")
        
        # Проверяем, что таблица создана правильно
        async with AsyncSessionLocal() as session:
            # Пробуем создать тестовую запись
            test_application = Application(
                full_name="Тест",
                phone="+7999999999",
                age=25,
                city="Тест",
                category="driver",
                experience="3",
                additional_info="Тестовая запись"
            )
            
            session.add(test_application)
            await session.commit()
            await session.refresh(test_application)
            
            logger.info(f"✅ Тестовая запись создана успешно: ID {test_application.id}")
            logger.info(f"📅 created_at: {test_application.created_at}")
            logger.info(f"📅 updated_at: {test_application.updated_at}")
            
            # Удаляем тестовую запись
            await session.delete(test_application)
            await session.commit()
            logger.info("🗑️ Тестовая запись удалена")
        
        logger.info("🎉 Схема базы данных успешно исправлена!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении схемы: {e}")
        import traceback
        logger.error(f"Подробности ошибки: {traceback.format_exc()}")
        raise
    finally:
        # Закрываем соединение
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_database()) 