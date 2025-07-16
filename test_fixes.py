#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений в обработчиках заявок
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from telegram_bot.services.manager_service import manager_service
from telegram_bot.config.settings import settings
from telegram_bot.models.support_models import ApplicationStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixes():
    """Тест исправлений"""
    try:
        logger.info("🔧 Тестируем исправления...")
        
        # Тестируем настройки
        logger.info(f"ADMIN_IDS: {settings.ADMIN_IDS}")
        logger.info(f"MANAGER_IDS: {settings.MANAGER_IDS}")
        logger.info(f"NOTIFICATION_CHAT_ID: {settings.NOTIFICATION_CHAT_ID}")
        
        # Тестируем получение менеджера
        test_telegram_id = 5161187711
        manager = await manager_service.get_manager_by_telegram_id(test_telegram_id)
        
        if manager:
            logger.info(f"✅ Менеджер найден: {manager.first_name}, admin: {manager.is_admin}")
            
            # Тестируем новые методы
            logger.info("🔍 Тестируем получение новых заявок...")
            new_apps = await manager_service.get_available_new_applications(limit=5)
            logger.info(f"📋 Найдено новых заявок: {len(new_apps)}")
            
            logger.info("🔍 Тестируем получение заявок менеджера...")
            manager_apps = await manager_service.get_manager_applications(test_telegram_id, limit=5)
            logger.info(f"📋 Заявок менеджера: {len(manager_apps)}")
            
            logger.info("🔍 Тестируем получение заявок со статусом NEW...")
            new_status_apps = await manager_service.get_manager_applications(
                test_telegram_id, 
                status=ApplicationStatus.NEW, 
                limit=5
            )
            logger.info(f"📋 NEW заявок для менеджера: {len(new_status_apps)}")
            
        else:
            logger.warning(f"❌ Менеджер с ID {test_telegram_id} не найден")
        
        logger.info("✅ Тестирование завершено!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_fixes()) 