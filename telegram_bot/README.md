# 🤖 ILPO-TAXI Telegram Support Bot

## 🎯 Описание

Telegram-бот для автоматизации работы менеджеров поддержки ILPO-TAXI. Интегрируется с основным сайтом для обработки заявок клиентов и обеспечивает переключение с ИИ-консультанта на живых менеджеров.

## ✨ Основные возможности

- 📋 **Автоматический прием заявок** с сайта
- 👨‍💼 **Управление менеджерами** и их статусами
- 🔄 **Автоназначение заявок** доступным менеджерам
- 💬 **Интеграция с веб-чатом** для переключения на менеджера
- 📊 **Статистика и аналитика** работы
- 🔔 **Система уведомлений** в реальном времени

## 🛠️ Технический стек

- **Framework:** aiogram 3.21.0
- **Database:** PostgreSQL 17 + SQLAlchemy 2.0
- **Cache:** Redis 7+
- **Migrations:** Alembic
- **Python:** 3.10+

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

### 3. Создание базы данных
```bash
# Применение миграций
alembic upgrade head
```

### 4. Запуск бота
```bash
python telegram_bot/main.py
```

## 📁 Структура проекта

```
telegram_bot/
├── config/          # Конфигурация и настройки
├── models/          # Модели базы данных
├── services/        # Бизнес-логика и сервисы
├── handlers/        # Обработчики команд и сообщений
├── utils/           # Утилиты и хелперы
├── main.py          # Основной файл запуска
└── README.md        # Этот файл

database/
├── migrations/      # Миграции Alembic
└── alembic.ini      # Конфигурация Alembic
```

## 🔧 Конфигурация

### Обязательные переменные окружения:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379
ADMIN_IDS=123456789,987654321
MANAGER_IDS=111111111,222222222
```

### Дополнительные настройки:
```bash
AUTO_ASSIGN_MANAGERS=true
MAX_ACTIVE_CHATS_PER_MANAGER=5
MANAGER_RESPONSE_TIME_LIMIT=300
```

## 📋 Команды бота

### Для менеджеров:
- `/start` - Главное меню и регистрация
- `/online` - Начать рабочую смену
- `/offline` - Завершить смену
- `/applications` - Просмотр заявок
- `/stats` - Личная статистика

### Для администраторов:
- `/admin` - Панель администратора
- `/managers` - Управление менеджерами
- `/reports` - Системные отчеты

## 🔄 Интеграция с сайтом

Бот автоматически получает заявки через:
1. **API endpoint** `/api/signup` в FastAPI
2. **Сервис заявок** создает записи в БД
3. **Автоназначение** менеджерам по алгоритму
4. **Telegram уведомления** менеджерам

## 💬 Веб-чат интеграция

Кнопка "Связаться с живым менеджером":
1. **Поиск** доступного менеджера
2. **Создание** чата поддержки в БД
3. **Передача истории** разговора с ИИ
4. **Уведомление** менеджера в Telegram

## 📊 Мониторинг

### Логи
```bash
# Логи бота
tail -f telegram_bot.log

# Системные логи
journalctl -u ilpo-taxi-bot -f
```

### Метрики Redis
```bash
redis-cli keys "manager_status:*"
redis-cli keys "chat_assignment:*"
```

### PostgreSQL
```sql
SELECT status, COUNT(*) FROM applications GROUP BY status;
SELECT status, COUNT(*) FROM managers GROUP BY status;
```

## 🛡️ Безопасность

- ✅ Проверка Telegram ID по whitelist
- ✅ Валидация прав доступа
- ✅ Логирование всех действий
- ✅ Шифрование чувствительных данных

## 📚 Документация

- [Подробная логика работы](TELEGRAM_BOT_LOGIC.md)
- [Настройка в production](../start.md#telegram-бот-поддержки)
- [Схема базы данных](models/support_models.py)

## 🤝 Разработка

### Создание миграций
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Тестирование
```bash
# Проверка подключений
python -c "from telegram_bot.config.settings import validate_settings; validate_settings()"

# Тест бота
python telegram_bot/main.py --test
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи бота
2. Убедитесь в корректности .env
3. Проверьте статус PostgreSQL и Redis
4. Обратитесь к документации

---

**Версия:** 1.0  
**Автор:** Senior Development Team  
**Проект:** ILPO-TAXI Smart Support System 