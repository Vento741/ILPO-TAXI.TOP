# 🚀 ILPO-TAXI Сервер - Шпаргалка разработчика

## 📋 Быстрый старт

### Подключение к серверу
```bash
# SSH подключение через веб-консоль Джино
# Или через терминал (если настроен SSH ключ):
ssh -p 49401 root@720a5024323f.vps.myjino.ru
```

### Переход в проект
```bash
cd /var/www/ILPO-TAXI.TOP
source venv/bin/activate
```

---

## 🔄 Git Workflow (Локально → Сервер)

### 1. Локальная разработка
```bash
# На локальной машине вносите изменения
git add .
git commit -m "Описание изменений"
git push origin main
```
# ОСТОРОЖНО! Это удалит все локальные изменения
git reset --hard HEAD
git pull origin main

### 2. Обновление на сервере
```bash
# На сервере обновляем код
cd /var/www/ILPO-TAXI.TOP
source venv/bin/activate

# Получаем изменения с GitHub
git pull origin main

# Если обновились зависимости - переустанавливаем
pip install -r requirements.txt
```

---

## 🔧 Управление сервисами

### Перезапуск FastAPI приложения
```bash
# Перезапуск основного сервиса
sudo systemctl restart ilpo-taxi

# Проверка статуса
sudo systemctl status ilpo-taxi

# Включение автозапуска (если нужно)
sudo systemctl enable ilpo-taxi
```

### Управление Nginx
```bash
# Перезапуск nginx
sudo systemctl restart nginx

# Перезагрузка конфигурации (без остановки)
sudo systemctl reload nginx

# Проверка конфигурации
sudo nginx -t

# Статус nginx
sudo systemctl status nginx
```

### Быстрый перезапуск всех сервисов
```bash
# Одной командой перезапускаем все
sudo systemctl restart ilpo-taxi nginx
```

---

## 📊 Мониторинг и логи

### Логи FastAPI приложения
```bash
# Логи в реальном времени
sudo journalctl -u ilpo-taxi -f

# Последние 50 строк
sudo journalctl -u ilpo-taxi -n 50

# Логи за последние 10 минут
sudo journalctl -u ilpo-taxi --since "10 minutes ago"

# Только ошибки
sudo journalctl -u ilpo-taxi -f -p err
```

### Логи Nginx
```bash
# Логи доступа (кто заходил)
sudo tail -f /var/log/nginx/access.log

# Логи ошибок
sudo tail -f /var/log/nginx/error.log

# Оба лога одновременно
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

### Мониторинг в реальном времени
```bash
# В разных терминалах запустите:

# Терминал 1: Логи приложения
sudo journalctl -u ilpo-taxi -f

# Терминал 2: Логи доступа nginx
sudo tail -f /var/log/nginx/access.log

# Терминал 3: Ошибки nginx
sudo tail -f /var/log/nginx/error.log
```

---

## 🛠️ Полезные команды

### Проверка работоспособности
```bash
# Проверяем что сайт отвечает
curl http://localhost/

# Проверяем сокет приложения
ls -la /tmp/ilpo-taxi.sock

# Проверяем процессы
sudo netstat -tlnp | grep :80
```

### Диагностика проблем
```bash
# Если сайт не работает, проверяем по порядку:

# 1. Статус сервисов
sudo systemctl status ilpo-taxi nginx

# 2. Конфигурация nginx
sudo nginx -t

# 3. Логи ошибок
sudo journalctl -u ilpo-taxi --no-pager -l | tail -20
sudo tail -20 /var/log/nginx/error.log

# 4. Проверка портов
sudo ss -tlnp | grep :80
```

### Управление файлами
```bash
# Права на файлы проекта
sudo chown -R root:www-data /var/www/ILPO-TAXI.TOP
sudo chmod -R 755 /var/www/ILPO-TAXI.TOP

# Проверка места на диске
df -h

# Размер проекта
du -sh /var/www/ILPO-TAXI.TOP/
```

---

## 🔒 Безопасность и SSL

### SSL сертификат (Let's Encrypt)
```bash
# Установка certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение SSL сертификата
sudo certbot --nginx -d ilpo-taxi.top -d www.ilpo-taxi.top

# Автообновление сертификата
sudo crontab -e
# Добавить: 0 12 * * * certbot renew --quiet
```

### Проверка SSL
```bash
# Тест SSL сертификата
sudo certbot certificates

# Проверка автообновления
sudo certbot renew --dry-run
```

---

## 📦 Обновление зависимостей

### Python пакеты
```bash
cd /var/www/ILPO-TAXI.TOP
source venv/bin/activate

# Обновление всех пакетов
pip install --upgrade -r requirements.txt

# Добавление нового пакета
pip install новый-пакет
pip freeze > requirements.txt
```

### Системные пакеты
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Очистка старых пакетов
sudo apt autoremove -y
sudo apt autoclean
```

---

## 🚨 Экстренные ситуации

### Быстрое восстановление
```bash
# Если что-то сломалось:

# 1. Перезапуск всех сервисов
sudo systemctl restart ilpo-taxi nginx

# 2. Откат к последней рабочей версии
git log --oneline -10  # смотрим коммиты
git reset --hard HASH_КОММИТА
sudo systemctl restart ilpo-taxi

# 3. Полная переустановка зависимостей
rm -rf venv/
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ilpo-taxi
```

### Мониторинг ресурсов
```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Активные процессы
ps aux | grep -E "(gunicorn|nginx)"

# Логи системы
sudo journalctl -f --since "1 hour ago"
```

---

## 🌐 URL и доступы

- **Сайт:** https://ilpo-taxi.top
- **IP сервера:** 81.177.6.46
- **API документация:** https://ilpo-taxi.top/docs
- **WebSocket чат:** wss://ilpo-taxi.top/ws/chat

### Файлы конфигурации
- **Nginx:** `/etc/nginx/conf.d/ilpo-taxi.conf`
- **Systemd:** `/etc/systemd/system/ilpo-taxi.service`
- **Проект:** `/var/www/ILPO-TAXI.TOP/`
- **Логи nginx:** `/var/log/nginx/`

---

## 📝 Workflow для разработки

### Ежедневная работа
1. **Локально:** Вносите изменения, тестируете
2. **Git:** `git add . && git commit -m "..." && git push`
3. **Сервер:** `git pull && sudo systemctl restart ilpo-taxi`
4. **Проверка:** Открываете сайт, смотрите логи

### При добавлении новых фич
1. Обновляете зависимости: `pip install -r requirements.txt`
2. Проверяете конфигурацию: `sudo nginx -t`
3. Перезапускаете сервисы: `sudo systemctl restart ilpo-taxi nginx`
4. Мониторите логи: `sudo journalctl -u ilpo-taxi -f`

---

## 🎯 Контрольный чек-лист

✅ **Перед деплоем:**
- [ ] Код работает локально
- [ ] Коммит запушен в git
- [ ] Все тесты проходят

✅ **После деплоя:**
- [ ] `git pull` выполнен
- [ ] Сервисы перезапущены
- [ ] Сайт открывается в браузере
- [ ] Чат работает
- [ ] Логи без ошибок

✅ **Еженедельно:**
- [ ] Обновление системы: `sudo apt update && sudo apt upgrade`
- [ ] Проверка SSL: `sudo certbot certificates`
- [ ] Анализ логов на ошибки

---

## 📞 В случае проблем

1. **Сначала:** Проверьте логи `sudo journalctl -u ilpo-taxi -f`
2. **Затем:** Перезапустите сервисы `sudo systemctl restart ilpo-taxi nginx`
3. **Если не помогло:** Откатитесь к рабочей версии через git
4. **Крайний случай:** Полная переустановка проекта

**Помните:** Всегда делайте бэкапы важных данных!

---

## 🤖 Telegram Бот Поддержки

### Настройка PostgreSQL 17

#### Установка PostgreSQL
```bash
# Установка PostgreSQL 17
sudo apt update
sudo apt install postgresql-17 postgresql-contrib-17

# Настройка пользователя
sudo -u postgres createuser --interactive
sudo -u postgres createdb ilpo_taxi

# Настройка пароля
sudo -u postgres psql
ALTER USER postgres PASSWORD 'your_secure_password';
\q
```

#### Создание базы данных
```bash
# Подключение к PostgreSQL
sudo -u postgres psql

# Создание базы данных для бота
CREATE DATABASE ilpo_taxi;
CREATE USER ilpo_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ilpo_taxi TO ilpo_user;

# Выход
\q
```

#### Настройка доступа
```bash
# Редактируем pg_hba.conf
sudo nano /etc/postgresql/17/main/pg_hba.conf

# Добавляем строку для локального доступа:
local   ilpo_taxi    ilpo_user                     md5

# Перезапускаем PostgreSQL
sudo systemctl restart postgresql
```

### Настройка Telegram Бота

#### 1. Создание бота
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Введите имя: `ILPO-TAXI Support Bot`
4. Введите username: `ilpo_taxi_support_bot`
5. Сохраните полученный токен

#### 2. Переменные окружения
```bash
# Добавьте в .env файл:
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_id,another_admin_id
MANAGER_IDS=manager1_id,manager2_id

# База данных
DATABASE_URL=postgresql+asyncpg://ilpo_user:secure_password@localhost:5432/ilpo_taxi
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=ilpo_taxi
DATABASE_USER=ilpo_user
DATABASE_PASSWORD=secure_password

# Redis
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

#### 3. Миграции базы данных
```bash
# Установка зависимостей
pip install -r requirements.txt

# Создание первой миграции
cd /var/www/ILPO-TAXI.TOP
alembic init database/migrations
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

#### 4. Запуск бота
```bash
# Создание systemd сервиса
sudo nano /etc/systemd/system/ilpo-taxi-bot.service

# Содержимое файла:
[Unit]
Description=ILPO-TAXI Telegram Support Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/ILPO-TAXI.TOP
Environment=PATH=/var/www/ILPO-TAXI.TOP/venv/bin
ExecStart=/var/www/ILPO-TAXI.TOP/venv/bin/python telegram_bot/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Запуск и автозапуск бота
sudo systemctl daemon-reload
sudo systemctl enable ilpo-taxi-bot
sudo systemctl start ilpo-taxi-bot

# Проверка статуса
sudo systemctl status ilpo-taxi-bot
```

### Управление ботом

#### Команды для менеджеров:
- `/start` - Главное меню
- `/online` - Начать рабочую смену
- `/offline` - Завершить смену
- `/applications` - Мои заявки
- `/stats` - Статистика работы

#### Команды для админов:
- `/admin` - Панель администратора
- `/managers` - Управление менеджерами
- `/reports` - Отчеты системы

### Логи и мониторинг

#### Логи бота
```bash
# Логи в реальном времени
sudo journalctl -u ilpo-taxi-bot -f

# Последние логи
sudo journalctl -u ilpo-taxi-bot -n 50

# Логи за сегодня
sudo journalctl -u ilpo-taxi-bot --since today
```

#### Логи PostgreSQL
```bash
# Логи PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-17-main.log

# Логи подключений
sudo grep "connection" /var/log/postgresql/postgresql-17-main.log
```

#### Мониторинг Redis
```bash
# Подключение к Redis
redis-cli

# Проверка активных ключей
keys *

# Информация о памяти
info memory
```

### Интеграция с сайтом

Бот автоматически получает заявки с сайта через:
- **API интеграцию** в `/api/signup`
- **Автоназначение** менеджерам
- **Уведомления** в Telegram

### Веб-чат интеграция

Кнопка "Связаться с живым менеджером" в веб-чате:
- **Автоматически** ищет доступного менеджера
- **Передает историю** разговора с ИИ
- **Уведомляет** менеджера в Telegram

### Troubleshooting

#### Бот не запускается:
```bash
# Проверяем зависимости
pip install -r requirements.txt

# Проверяем переменные окружения
cat .env | grep TELEGRAM

# Проверяем логи
sudo journalctl -u ilpo-taxi-bot --since "1 hour ago"
```

#### Проблемы с БД:
```bash
# Проверяем подключение к PostgreSQL
sudo -u postgres psql -d ilpo_taxi_db -c "SELECT version();"

# Проверяем таблицы
sudo -u postgres psql -d ilpo_taxi_db -c "\dt"

# Если таблиц нет - создаем их
python telegram_bot/init_db.py

# Или применяем миграции заново
alembic upgrade head
```

#### Заявки не приходят в Telegram:
```bash
# 1. Проверяем логи основного приложения
sudo journalctl -u ilpo-taxi -f | grep "заявка"

# 2. Проверяем статус бота
sudo systemctl status ilpo-taxi-bot

# 3. Проверяем подключение к БД
python telegram_bot/init_db.py

# 4. Перезапускаем бота
sudo systemctl restart ilpo-taxi-bot

# 5. Тестируем интеграцию с Telegram ботом
python telegram_bot/test_integration.py

# 6. Или прямой тест API
curl -X POST http://localhost/api/signup \
  -H "Content-Type: application/json" \
  -d '{"fullName":"Тест","phone":"+79991234567","age":"25","city":"Тест","category":"driver","experience":"5"}'
```

#### Проблемы с Redis:
```bash
# Проверяем статус Redis
sudo systemctl status redis

# Тест подключения
redis-cli ping

# Очистка кэша (осторожно!)
redis-cli flushall
```

---

## 🚨 БЫСТРОЕ ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С ЗАЯВКАМИ

```bash
# СРОЧНЫЙ ФИКС - выполните по порядку:

# 1. На СЕРВЕРЕ - инициализируем БД
cd /var/www/ILPO-TAXI.TOP
source venv/bin/activate
python telegram_bot/init_db.py

# 2. Перезапускаем Telegram бота
sudo systemctl restart ilpo-taxi-bot

# 3. Проверяем работу
python telegram_bot/test_integration.py

# 4. Если всё работает - применяем к коду на сервере:
git add .
git commit -m "fix: исправлены JavaScript ошибки и интеграция с Telegram ботом"
git push origin main
```

---

## 📊 Полная схема перезапуска всех сервисов

```bash
# Последовательность перезапуска всех компонентов:

# 1. Обновляем код
cd /var/www/ILPO-TAXI.TOP
git pull origin main

# 2. Обновляем зависимости Python
source venv/bin/activate
pip install -r requirements.txt

# 3. Применяем миграции БД (если есть)
alembic upgrade head

# 4. Инициализируем БД (если нужно)
python telegram_bot/init_db.py

# 5. Перезапускаем все сервисы
sudo systemctl restart postgresql redis nginx ilpo-taxi ilpo-taxi-bot

# 6. Проверяем статусы
sudo systemctl status postgresql redis nginx ilpo-taxi ilpo-taxi-bot
```

**Помните:** Всегда делайте бэкапы важных данных!