#!/usr/bin/env python3
"""
Проверка настроек Telegram бота
"""
import sys
import os
sys.path.append('/var/www/ILPO-TAXI.TOP')

from telegram_bot.config.settings import settings

print("🔍 Проверка настроек Telegram бота:")
print(f"📱 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:20]}...")
print(f"📊 Database URL: {settings.DATABASE_URL}")
print(f"🔴 Redis URL: {settings.REDIS_URL}")
print()
print("👑 Администраторы:")
print(f"   ADMIN_IDS_STR: '{settings.ADMIN_IDS_STR}'")
print(f"   Parsed ADMIN_IDS: {settings.ADMIN_IDS}")
print()
print("👥 Менеджеры:")
print(f"   MANAGER_IDS_STR: '{settings.MANAGER_IDS_STR}'")
print(f"   Parsed MANAGER_IDS: {settings.MANAGER_IDS}")
print()

if settings.ADMIN_IDS:
    print("✅ Админы настроены правильно")
else:
    print("❌ Админы не настроены!")

if settings.MANAGER_IDS:
    print("✅ Менеджеры настроены правильно")
else:
    print("❌ Менеджеры не настроены!") 