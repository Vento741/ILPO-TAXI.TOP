"""
Конфигурация Telegram-бота поддержки ILPO-TAXI
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator

# Удаляем этот load_dotenv(), так как он уже есть в main.py и Systemd

class Settings(BaseSettings):
    """Настройки приложения"""
    model_config = {"extra": "allow", "env_file": ".env", "case_sensitive": True}
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_URL: str = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # OpenRouter API
    OPENROUTER_API_KEY_CONSULTANT: str = os.getenv("OPENROUTER_API_KEY_CONSULTANT", "")
    OPENROUTER_API_KEY_SEARCH: str = os.getenv("OPENROUTER_API_KEY_SEARCH", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/ilpo_taxi")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ilpo_taxi")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # FastAPI Integration
    FASTAPI_URL: str = os.getenv("FASTAPI_URL", "http://localhost:8000")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "your-secret-key")
    
        # Admin Users (Telegram IDs) - строки, будут парситься в списки
    ADMIN_IDS_STR: str = os.getenv("ADMIN_IDS", "")
    MANAGER_IDS_STR: str = os.getenv("MANAGER_IDS", "")

    # Business Logic
    AUTO_ASSIGN_MANAGERS: bool = True
    MAX_ACTIVE_CHATS_PER_MANAGER: int = 5
    MANAGER_RESPONSE_TIME_LIMIT: int = 300  # 5 минут
    
    # Notifications
    NOTIFICATION_CHAT_ID: int = int(os.getenv("NOTIFICATION_CHAT_ID", "0"))

    @property
    def ADMIN_IDS(self) -> List[int]:
        """Парсит ADMIN_IDS из строки в список int"""
        if not self.ADMIN_IDS_STR:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS_STR.split(',') if x.strip()]
    
    @property
    def MANAGER_IDS(self) -> List[int]:
        """Парсит MANAGER_IDS из строки в список int"""
        if not self.MANAGER_IDS_STR:
            return []
        return [int(x.strip()) for x in self.MANAGER_IDS_STR.split(',') if x.strip()]

# Создаем экземпляр настроек
settings = Settings()

# Проверка обязательных настроек
def validate_settings():
    """Проверяет наличие обязательных настроек"""
    required_settings = {
        'TELEGRAM_BOT_TOKEN': settings.TELEGRAM_BOT_TOKEN,
        'DATABASE_URL': settings.DATABASE_URL,
        'REDIS_URL': settings.REDIS_URL,
    }
    
    missing = [key for key, value in required_settings.items() if not value]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return True 