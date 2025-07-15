# ✅ Быстрый чеклист развертывания ILPO-TAXI

## 🔧 Перед отправкой на сервер

### 1. Обновите `.env` файл
- [ ] `TELEGRAM_BOT_TOKEN` - получите у @BotFather
- [ ] `DATABASE_PASSWORD` - придумайте надежный пароль
- [ ] `REDIS_PASSWORD` - придумайте пароль для Redis
- [ ] `API_SECRET_KEY` - генерируйте случайную строку 32+ символов
- [ ] `JWT_SECRET_KEY` - генерируйте случайную строку 32+ символов  
- [ ] `ADMIN_IDS` - ваши Telegram ID (получите через @userinfobot)
- [ ] `MANAGER_IDS` - Telegram ID менеджеров поддержки
- [ ] `DEBUG=False` - установите для продакшн

### 2. Получите Telegram ID
```bash
# Отправьте /start боту @userinfobot в Telegram
# Скопируйте ваш ID в ADMIN_IDS
```

### 3. Создайте Telegram бота
```bash
# 1. Напишите @BotFather в Telegram
# 2. Команда: /newbot
# 3. Укажите имя: ILPO-TAXI Support Bot
# 4. Укажите username: ilpo_taxi_support_bot
# 5. Скопируйте токен в TELEGRAM_BOT_TOKEN
```

## 🖥️ На сервере

### 1. Системные зависимости
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3.10 python3.10-venv python3-pip postgresql postgresql-contrib redis-server nginx certbot python3-certbot-nginx -y
```

### 2. База данных PostgreSQL
```bash
sudo -u postgres psql
CREATE USER ilpo_user WITH PASSWORD 'your_password_here';
CREATE DATABASE ilpo_taxi_db OWNER ilpo_user;
GRANT ALL PRIVILEGES ON DATABASE ilpo_taxi_db TO ilpo_user;
\q
```

### 3. Redis пароль
```bash
sudo nano /etc/redis/redis.conf
# Найдите: # requirepass foobared
# Замените на: requirepass your_redis_password_here
sudo systemctl restart redis
```

### 4. Проект
```bash
sudo mkdir -p /var/www/ilpo-taxi
sudo chown $USER:$USER /var/www/ilpo-taxi
cd /var/www/ilpo-taxi
# Загрузите ваш код сюда

python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn uvloop
```

### 5. Миграции
```bash
alembic -c database/alembic.ini upgrade head
```

### 6. Systemd сервисы

#### FastAPI сервис
```bash
sudo nano /etc/systemd/system/ilpo-taxi-api.service
```
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

[Install]
WantedBy=multi-user.target
```

#### Telegram Bot сервис
```bash
sudo nano /etc/systemd/system/ilpo-taxi-bot.service
```
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

[Install]
WantedBy=multi-user.target
```

### 7. Nginx конфигурация
```bash
sudo nano /etc/nginx/sites-available/ilpo-taxi
```
```nginx
server {
    listen 80;
    server_name ilpo-taxi.top www.ilpo-taxi.top;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ilpo-taxi.top www.ilpo-taxi.top;

    ssl_certificate /etc/letsencrypt/live/ilpo-taxi.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ilpo-taxi.top/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 8. SSL сертификат
```bash
sudo certbot --nginx -d ilpo-taxi.top -d www.ilpo-taxi.top
```

### 9. Запуск
```bash
sudo ln -s /etc/nginx/sites-available/ilpo-taxi /etc/nginx/sites-enabled/
sudo nginx -t
sudo chown -R www-data:www-data /var/www/ilpo-taxi

sudo systemctl daemon-reload
sudo systemctl enable ilpo-taxi-api ilpo-taxi-bot
sudo systemctl start ilpo-taxi-api ilpo-taxi-bot
sudo systemctl reload nginx
```

### 10. Проверка
```bash
sudo systemctl status ilpo-taxi-api
sudo systemctl status ilpo-taxi-bot
curl https://ilpo-taxi.top
```

### 11. Настройка Telegram webhook
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://ilpo-taxi.top/webhook/telegram"}'
```

## 🚨 После запуска

- [ ] Проверьте сайт: https://ilpo-taxi.top
- [ ] Протестируйте бота в Telegram
- [ ] Отправьте `/start` боту от админ аккаунта
- [ ] Проверьте логи: `sudo journalctl -u ilpo-taxi-api -f`
- [ ] Настройте firewall: `sudo ufw enable && sudo ufw allow ssh && sudo ufw allow 'Nginx Full'`
- [ ] Настройте автообновление SSL: `sudo certbot renew --dry-run`

## 🔍 Основные команды для отладки

```bash
# Логи сервисов
sudo journalctl -u ilpo-taxi-api -f
sudo journalctl -u ilpo-taxi-bot -f

# Перезапуск сервисов
sudo systemctl restart ilpo-taxi-api
sudo systemctl restart ilpo-taxi-bot

# Проверка статуса
sudo systemctl status ilpo-taxi-api
sudo systemctl status ilpo-taxi-bot

# Тест подключения к БД
psql -U ilpo_user -h localhost -d ilpo_taxi_db

# Тест Redis
redis-cli -a your_redis_password_here ping
``` 