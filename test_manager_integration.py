#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции веб-чата с менеджерами
"""
import asyncio
import aiohttp
import json
from datetime import datetime

# Тестовые данные
TEST_SESSION_ID = f"test_session_{int(datetime.now().timestamp())}"
TEST_BASE_URL = "http://localhost"  # Измените на ваш URL

async def test_manager_transfer():
    """Тест переключения на менеджера"""
    print("🧪 Тестирование переключения на менеджера...")
    
    async with aiohttp.ClientSession() as session:
        # Подготавливаем тестовую историю чата
        chat_history = [
            {
                "role": "user",
                "content": "Привет! Хочу подключиться к Яндекс.Такси",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant", 
                "content": "Привет! Помогу с подключением к Яндекс.Такси. Какие у вас есть вопросы?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "user",
                "content": "Какие документы нужны?",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Тест переключения на менеджера
        transfer_data = {
            "session_id": TEST_SESSION_ID,
            "chat_history": chat_history,
            "client_name": "Тест Тестович",
            "client_phone": "+79991234567"
        }
        
        try:
            async with session.post(
                f"{TEST_BASE_URL}/api/chat/transfer-to-manager",
                json=transfer_data
            ) as response:
                result = await response.json()
                
                if result.get("success"):
                    print(f"✅ Переключение успешно!")
                    print(f"   Менеджер: {result.get('manager_name')}")
                    print(f"   Chat ID: {result.get('chat_id')}")
                    print(f"   Support Chat ID: {result.get('support_chat_id')}")
                    
                    return result.get('chat_id')
                else:
                    print(f"❌ Ошибка переключения: {result.get('error')}")
                    print(f"   Сообщение: {result.get('message')}")
                    return None
                    
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return None

async def test_send_message(chat_id: str):
    """Тест отправки сообщения менеджеру"""
    if not chat_id:
        print("⚠️ Пропускаем тест отправки сообщения - нет chat_id")
        return
        
    print("\n📨 Тестирование отправки сообщения менеджеру...")
    
    async with aiohttp.ClientSession() as session:
        message_data = {
            "chat_id": chat_id,
            "message_text": "Это тестовое сообщение от веб-клиента. Менеджер должен получить его в Telegram!",
            "client_name": "Тест Тестович"
        }
        
        try:
            async with session.post(
                f"{TEST_BASE_URL}/api/chat/send-message",
                json=message_data
            ) as response:
                result = await response.json()
                
                if result.get("success"):
                    print("✅ Сообщение отправлено менеджеру!")
                    print(f"   Ответ: {result.get('message')}")
                else:
                    print(f"❌ Ошибка отправки: {result.get('error')}")
                    
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестов интеграции менеджеров ILPO-TAXI\n")
    
    # Тест 1: Переключение на менеджера
    chat_id = await test_manager_transfer()
    
    # Небольшая пауза
    await asyncio.sleep(2)
    
    # Тест 2: Отправка сообщения
    await test_send_message(chat_id)
    
    print("\n✨ Тестирование завершено!")
    print("\n📋 Что нужно проверить вручную:")
    print("1. Менеджер получил уведомление в Telegram")
    print("2. Менеджер может принять чат через кнопки")
    print("3. Менеджер получил тестовое сообщение")
    print("4. Менеджер может ответить и сообщение дойдет до веб-клиента")

if __name__ == "__main__":
    print("⚠️  УБЕДИТЕСЬ, ЧТО:")
    print("1. Сервер запущен (python main.py)")
    print("2. Telegram бот запущен (python telegram_bot/main.py)")
    print("3. В системе есть онлайн менеджеры")
    print("4. PostgreSQL и Redis работают")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}") 