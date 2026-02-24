# 🤖 Логика работы Telegram-бота поддержки ILPO-TAXI

## 🎯 Общая концепция

Telegram-бот поддержки ILPO-TAXI предназначен для автоматизации работы менеджеров с клиентскими заявками и обеспечения круглосуточной поддержки. Бот интегрируется с основным сайтом и веб-чатом.

## 📋 Основные функции

### 1. Управление заявками
- **Автоматический прием заявок** с сайта ilpo-taxi.top
- **Автоназначение** заявок доступным менеджерам
- **Уведомления** менеджеров о новых заявках
- **Трекинг статусов** заявок (новая → назначена → в работе → завершена)

### 2. Система менеджеров
- **Регистрация** новых менеджеров
- **Управление статусами** (онлайн/офлайн/занят)
- **Распределение нагрузки** между менеджерами
- **Статистика работы** и KPI

### 3. Интеграция с веб-чатом
- **Переключение с ИИ на менеджера** по запросу клиента
- **Передача истории** разговора с ИИ-консультантом
- **Двусторонняя синхронизация** сообщений
- **Уведомления** менеджеров о веб-чатах

## 🔄 Схема работы

### Поток заявок с сайта:
```
Сайт → API → PostgreSQL → Автоназначение → Уведомление менеджера → Обработка
```

### Поток веб-чата:
```
Веб-чат → Запрос менеджера → Поиск доступного → Уведомление → Переключение
```

## 👥 Роли пользователей

### 🏢 Администраторы
- Управление менеджерами
- Просмотр общей статистики
- Настройка системы
- Мониторинг работы

**Команды:**
- `/admin` - Панель администратора
- `/managers` - Управление менеджерами  
- `/reports` - Отчеты и аналитика
- `/settings` - Настройки системы

### 👨‍💼 Менеджеры
- Обработка заявок клиентов
- Ведение чатов поддержки
- Управление своим статусом
- Просмотр личной статистики

**Команды:**
- `/start` - Главное меню
- `/online` - Начать рабочую смену
- `/offline` - Завершить смену
- `/applications` - Мои заявки
- `/stats` - Моя статистика

## 🗃️ Структура базы данных

### Основные таблицы:

#### `applications` - Заявки клиентов
```sql
- id (PK)
- full_name
- phone
- city
- category (driver/courier/both/cargo)
- status (new/assigned/in_progress/completed)
- assigned_manager_id (FK)
- created_at
```

#### `managers` - Менеджеры поддержки
```sql
- id (PK)
- telegram_id (unique)
- first_name, last_name
- status (online/offline/busy)
- is_admin
- max_active_chats
- total_applications
```

#### `support_chats` - Чаты поддержки
```sql
- id (PK)
- chat_id (unique)
- chat_type (web_chat/telegram_direct/transfer_from_ai)
- manager_id (FK)
- application_id (FK)
- is_active
```

#### `chat_messages` - Сообщения в чатах
```sql
- id (PK)
- chat_id (FK)
- sender_type (client/manager/system)
- message_text
- created_at
```

## ⚙️ Алгоритмы работы

### 🎯 Автоназначение заявок

```python
def auto_assign_application(application_id):
    # 1. Найти доступных менеджеров (статус = online)
    available_managers = get_online_managers()
    
    # 2. Отфильтровать по загруженности
    managers_with_capacity = filter_by_active_chats(available_managers)
    
    # 3. Выбрать менеджера с наименьшей нагрузкой
    best_manager = min(managers_with_capacity, key=lambda m: m.active_chats)
    
    # 4. Назначить заявку
    assign_application(application_id, best_manager.id)
    
    # 5. Уведомить менеджера
    notify_manager(best_manager.telegram_id, application_id)
```

### 🔄 Переключение веб-чата на менеджера

```python
def transfer_web_chat_to_manager(session_id, chat_history):
    # 1. Найти доступного менеджера
    manager = get_available_manager()
    
    if not manager:
        return {"success": False, "message": "Все менеджеры заняты"}
    
    # 2. Создать чат в БД
    chat = create_support_chat(
        type="transfer_from_ai",
        manager_id=manager.id,
        metadata={"web_session": session_id, "history": chat_history}
    )
    
    # 3. Добавить в активные чаты менеджера
    add_active_chat(manager.telegram_id, chat.id)
    
    # 4. Уведомить менеджера
    notify_manager_about_web_chat(manager.telegram_id, chat_history)
    
    return {"success": True, "manager": manager.name}
```

## 🕐 Рабочие смены менеджеров

### Начало смены (`/online`):
1. Проверка регистрации менеджера
2. Создание записи `ManagerWorkSession`
3. Установка статуса `ONLINE`
4. Уведомление о готовности принимать заявки

### Завершение смены (`/offline`):
1. Проверка активных чатов
2. Предупреждение о передаче чатов (если есть)
3. Обновление `ManagerWorkSession.ended_at`
4. Установка статуса `OFFLINE`
5. Очистка активных чатов в Redis

## 📊 Система уведомлений

### Менеджерам:
- 🔔 Новая заявка назначена
- 💬 Новый веб-чат передан
- ⏰ Долгое время без ответа
- 📈 Сводка за смену

### Администраторам:
- 🚀 Запуск/остановка бота
- 📊 Ежедневные отчеты
- ⚠️ Ошибки системы
- 📈 Общая статистика

## 🔧 Настройки и конфигурация

### Переменные окружения:
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
MANAGER_IDS=111111111,222222222

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379

# Business Logic
AUTO_ASSIGN_MANAGERS=true
MAX_ACTIVE_CHATS_PER_MANAGER=5
MANAGER_RESPONSE_TIME_LIMIT=300
```

## 🚀 Развертывание

### 1. Подготовка базы данных:
```bash
# Создание миграций
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

### 2. Запуск бота:
```bash
# Основной бот
python telegram_bot/main.py

# Или через systemd (рекомендуется)
systemctl start ilpo-taxi-bot
```

### 3. Интеграция с сайтом:
- Добавить переменные окружения
- Обновить роуты API
- Перезапустить FastAPI

## 📈 Мониторинг и отладка

### Логи бота:
```bash
# Логи в реальном времени
journalctl -u ilpo-taxi-bot -f

# Логи файловые
tail -f telegram_bot.log
```

### Метрики Redis:
```bash
# Активные сессии
redis-cli keys "manager_status:*"

# Активные чаты
redis-cli keys "chat_assignment:*"
```

### PostgreSQL метрики:
```sql
-- Статистика заявок
SELECT status, COUNT(*) FROM applications GROUP BY status;

-- Активные менеджеры
SELECT status, COUNT(*) FROM managers GROUP BY status;

-- Производительность менеджеров
SELECT m.first_name, COUNT(a.id) as applications_count
FROM managers m
LEFT JOIN applications a ON a.assigned_manager_id = m.id
GROUP BY m.id, m.first_name;
```

## 🛡️ Безопасность

### Аутентификация:
- Проверка Telegram ID по whitelist
- Валидация прав доступа для команд
- Защита от спама (rate limiting)

### Данные:
- Шифрование чувствительной информации
- Логирование всех действий
- Регулярные бэкапы БД

## 🔮 Планы развития

### Ближайшие:
- [ ] Веб-интерфейс для менеджеров
- [ ] SMS уведомления клиентам
- [ ] Интеграция с CRM системами
- [ ] Аналитический дашборд

### Долгосрочные:
- [ ] ИИ-помощник для менеджеров
- [ ] Голосовые сообщения
- [ ] Интеграция с телефонией
- [ ] Мобильное приложение

---

**Автор:** Senior Developer Team  
**Версия:** 1.0  
**Дата:** 2025  
**Проект:** ILPO-TAXI Smart Support System 
