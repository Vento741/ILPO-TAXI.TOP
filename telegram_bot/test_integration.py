#!/usr/bin/env python3
"""
Тестирование интеграции Telegram бота с сайтом
"""
import asyncio
import json
import logging
from telegram_bot.services.application_service import handle_new_application_from_site

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_application_creation():
    """Тест создания заявки"""
    test_data = {
        "fullName": "Тестов Тест Тестович",
        "phone": "+7 (999) 123-45-67",
        "age": "25",
        "city": "Тест-город",
        "category": "driver",
        "experience": "5",
        "citizenship": "rf",
        "workStatus": "self_employed",
        "hasLicense": "on",
        "hasCar": "on",
        "carModel": "Тест-авто",
        "hasDocuments": "on",
        "agreeTerms": "on",
        "agreeNewsletter": "on"
    }
    
    logger.info("🧪 Тестируем создание заявки...")
    logger.info(f"📝 Тестовые данные: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        result = await handle_new_application_from_site(test_data)
        if result:
            logger.info("✅ Тест успешен! Заявка создана и отправлена в Telegram")
            return True
        else:
            logger.error("❌ Тест провален! Заявка не была создана")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка во время теста: {e}")
        import traceback
        logger.error(f"Подробности: {traceback.format_exc()}")
        return False

async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестирования интеграции...")
    
    success = await test_application_creation()
    
    if success:
        logger.info("🎉 Все тесты прошли успешно!")
    else:
        logger.error("💥 Тесты провалены! Проверьте настройки базы данных и Telegram бота")

if __name__ == "__main__":
    asyncio.run(main()) 