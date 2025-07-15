#!/usr/bin/env python3
"""
Создание записи менеджера в базе данных
"""
import asyncio
import sys
import os
sys.path.append('/var/www/ILPO-TAXI.TOP')

from telegram_bot.models.database import AsyncSessionLocal
from telegram_bot.models.support_models import Manager, ManagerStatus
from telegram_bot.config.settings import settings

async def create_manager_from_settings():
    """Создает менеджеров из настроек .env"""
    async with AsyncSessionLocal() as session:
        try:
            # Создаем менеджеров для всех ID из настроек
            for telegram_id in settings.MANAGER_IDS:
                # Проверяем, не существует ли уже (ищем по telegram_id, а не по id)
                from sqlalchemy import select
                result = await session.execute(
                    select(Manager).where(Manager.telegram_id == telegram_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    print(f"✅ Менеджер {telegram_id} уже существует")
                    continue
                
                # Создаем нового менеджера
                manager = Manager(
                    telegram_id=telegram_id,
                    name=f"Manager_{telegram_id}",
                    status=ManagerStatus.ONLINE
                )
                
                session.add(manager)
                print(f"➕ Создан менеджер: {telegram_id}")
            
            await session.commit()
            print("✅ Все менеджеры созданы успешно!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка создания менеджеров: {e}")
            import traceback
            print(f"Подробности: {traceback.format_exc()}")

async def main():
    print("🔧 Создание менеджеров из настроек...")
    print(f"📋 Manager IDs: {settings.MANAGER_IDS}")
    
    if not settings.MANAGER_IDS:
        print("❌ Не найдены ID менеджеров в настройках!")
        return
    
    await create_manager_from_settings()

if __name__ == "__main__":
    asyncio.run(main()) 