# 🚀 Инструкция по развертыванию ILPO-TAXI на сервере

## 📋 Подготовка к развертыванию

### 1. Обновите `.env` файл
Замените следующие значения в `.env` файле:

#### 🔑 Обязательные настройки:
```bash
# Получите у @BotFather в Telegram
TELEGRAM_BOT_TOKEN=YOUR_REAL_BOT_TOKEN

# Ваши реальные данные PostgreSQL
DATABASE_PASSWORD=your_strong_password_here
DATABASE_USER=ilpo_user
DATABASE_NAME=ilpo_taxi_db

# Пароль для Redis
REDIS_PASSWORD=your_redis_password_here

# Секретные ключи (генерируйте случайные)
API_SECRET_KEY=your_super_secret_api_key_minimum_32_characters_long
JWT_SECRET_KEY=your_jwt_secret_key_for_tokens_very_long_and_secure

# Получите через @userinfobot в Telegram
ADMIN_IDS=123456789,987654321
MANAGER_IDS=111111111,222222222

# Установите False для продакшн
DEBUG=False
```

## 🖥️ Установка на сервер Ubuntu/Debian

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка Python 3.10+
```bash
sudo apt install python3.10 python3.10-venv python3-pip -y
```

### 3. Установка PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создание пользователя и базы данных
sudo -u postgres psql
```

В PostgreSQL консоли:
```sql
CREATE USER ilpo_user WITH PASSWORD 'your_strong_password_here';
CREATE DATABASE ilpo_taxi_db OWNER ilpo_user;
GRANT ALL PRIVILEGES ON DATABASE ilpo_taxi_db TO ilpo_user;
\q
```

### 4. Установка Redis
```bash
sudo apt install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis

# Настройка пароля Redis
sudo nano /etc/redis/redis.conf
# Найдите и раскомментируйте: requirepass your_redis_password_here
sudo systemctl restart redis
```

### 5. Установка Nginx
```bash
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
```

## 📁 Развертывание проекта

### 1. Создание директории проекта
```bash
sudo mkdir -p /var/www/ilpo-taxi
sudo chown $USER:$USER /var/www/ilpo-taxi
cd /var/www/ilpo-taxi
```

### 2. Клонирование проекта
```bash
# Загрузите ваш проект на сервер
git clone YOUR_REPOSITORY_URL .
# или загрузите архив и распакуйте
```

### 3. Создание виртуального окружения
```bash
python3.10 -m venv venv
source venv/bin/activate
```

### 4. Установка зависимостей
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvloop
```

### 5. Настройка переменных окружения
```bash
# Скопируйте ваш обновленный .env файл
cp .env.example .env
nano .env
# Вставьте ваши настройки
```

### 6. Запуск миграций базы данных
```bash
# Применение миграций
alembic -c database/alembic.ini upgrade head
```

## 🔧 Настройка сервисов

### 1. Создание systemd сервиса для FastAPI
```bash
sudo nano /etc/systemd/system/ilpo-taxi-api.service
```

Содержимое файла:
```ini
[Unit]
Description=ILPO-TAXI FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/ilpo-taxi
Environment=PATH=/var/www/ilpo-taxi/venv/bin
EnvironmentFile=/var/www/ilpo-taxi/.env
ExecStart=/var/www/ilpo-taxi/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Создание systemd сервиса для Telegram бота
```bash
sudo nano /etc/systemd/system/ilpo-taxi-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=ILPO-TAXI Telegram Bot
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/ilpo-taxi/telegram_bot
Environment=PATH=/var/www/ilpo-taxi/venv/bin
EnvironmentFile=/var/www/ilpo-taxi/.env
ExecStart=/var/www/ilpo-taxi/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Настройка Nginx
```bash
sudo nano /etc/nginx/sites-available/ilpo-taxi
```

Содержимое файла:
```nginx
# Сначала делаем резервную копию
sudo cp /etc/nginx/sites-available/ilpo-taxi /etc/nginx/sites-available/ilpo-taxi.backup

# Заменяем конфигурацию с учетом IP-адреса
sudo tee /etc/nginx/sites-available/ilpo-taxi > /dev/null << 'EOF'
# HTTP сервер - редирект на HTTPS
server {
    listen 80;
    server_name ilpo-taxi.top www.ilpo-taxi.top 81.177.6.46;

    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS сервер - основная конфигурация
server {
    listen 443 ssl http2;
    server_name ilpo-taxi.top www.ilpo-taxi.top 81.177.6.46;

    # SSL сертификаты (будем настраивать Let's Encrypt позже)
    ssl_certificate /etc/letsencrypt/live/ilpo-taxi.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ilpo-taxi.top/privkey.pem;

    # SSL настройки безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Основное приложение FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Webhook для Telegram бота
    location /webhook/telegram {
        proxy_pass http://127.0.0.1:8000/webhook/telegram;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Статические файлы (CSS, JS, изображения)
    location /static/ {
        alias /var/www/ILPO-TAXI.TOP/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Настройки для статических файлов
        location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Uploaded files (if any)
    location /uploads/ {
        alias /var/www/ILPO-TAXI.TOP/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Disable execution of scripts
        location ~* \.(php|pl|py|jsp|asp|sh|cgi)$ {
            deny all;
        }
    }

    # Disable nginx version
    server_tokens off;
    
    # Default security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF
```

### 4. Активация конфигурации Nginx
```bash
sudo ln -s /etc/nginx/sites-available/ilpo-taxi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 Настройка SSL сертификата

### Установка Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Получение SSL сертификата
```bash
sudo certbot --nginx -d ilpo-taxi.top -d www.ilpo-taxi.top
```

## 🚀 Запуск сервисов

### 1. Установка прав доступа
```bash
sudo chown -R www-data:www-data /var/www/ilpo-taxi
sudo chmod -R 755 /var/www/ilpo-taxi
```

### 2. Создание директории для логов
```bash
sudo mkdir -p /var/log/ilpo-taxi
sudo chown www-data:www-data /var/log/ilpo-taxi
```

### 3. Запуск сервисов
```bash
sudo systemctl daemon-reload
sudo systemctl enable ilpo-taxi-api
sudo systemctl enable ilpo-taxi-bot
sudo systemctl start ilpo-taxi-api
sudo systemctl start ilpo-taxi-bot
```

### 4. Проверка статуса
```bash
sudo systemctl status ilpo-taxi-api
sudo systemctl status ilpo-taxi-bot
```

## 📊 Мониторинг и логи

### Просмотр логов
```bash
# Логи FastAPI
sudo journalctl -u ilpo-taxi-api -f

# Логи Telegram бота
sudo journalctl -u ilpo-taxi-bot -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🔧 Первоначальная настройка

### 1. Регистрация администратора
После запуска бота отправьте команду `/start` боту от аккаунта администратора.

### 2. Настройка webhook для Telegram
```bash
# Через curl или в браузере
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://ilpo-taxi.top/webhook/telegram"}'
```

## 🛡️ Безопасность

### 1. Настройка firewall
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
```

### 2. Регулярные обновления
```bash
# Добавьте в crontab
sudo crontab -e
# 0 4 * * 0 apt update && apt upgrade -y
```

## 📝 Полезные команды

### Перезапуск сервисов
```bash
sudo systemctl restart ilpo-taxi-api
sudo systemctl restart ilpo-taxi-bot
sudo systemctl reload nginx
```

### Обновление кода
```bash
cd /var/www/ilpo-taxi
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
alembic -c database/alembic.ini upgrade head
sudo systemctl restart ilpo-taxi-api
sudo systemctl restart ilpo-taxi-bot
```

### Резервное копирование базы данных
```bash
pg_dump -U ilpo_user -h localhost ilpo_taxi_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

## ❗ Важные замечания

1. **Замените все пароли** в `.env` файле на надежные
2. **Настройте регулярные бэкапы** базы данных
3. **Мониторьте логи** на предмет ошибок
4. **Обновляйте систему** регулярно
5. **Тестируйте функциональность** после развертывания

## 🆘 Troubleshooting

### Проблемы с подключением к базе данных
```bash
# Проверьте статус PostgreSQL
sudo systemctl status postgresql

# Проверьте подключение
psql -U ilpo_user -h localhost -d ilpo_taxi_db
```

### Проблемы с Redis
```bash
# Проверьте статус Redis
sudo systemctl status redis

# Тест подключения
redis-cli -a your_redis_password_here ping
```

### Проблемы с сертификатом
```bash
# Обновление сертификата
sudo certbot renew --dry-run
``` 