# 📖 Документация ilpo-taxi.top

## 🎯 О проекте

**ilpo-taxi.top** — это **"Умный Таксопарк"** нового поколения с интегрированным ИИ-агентом для подключения водителей, курьеров и доставщиков к официальному партнеру Яндекс.Такси по всей России.

### 🤖 Ключевые инновации:
- ✅ **ИИ-консультант** — персональный помощник 24/7 для каждого клиента
- ✅ **Умные рекомендации** — ИИ подбирает оптимальный статус и регион работы
- ✅ **Автоматизированный документооборот** — ИИ помогает заполнить заявки и проверить документы
- ✅ **Прогнозирование заработка** — ИИ рассчитывает потенциальный доход по регионам
- ✅ **Персонализированное обучение** — ИИ создает индивидуальные планы адаптации

### 🚀 Традиционные преимущества:
- ✅ **Официальный партнер** Яндекс.Про с 2022 года
- ✅ **Все регионы России** — от Москвы до самых отдаленных городов
- ✅ **Множественные сервисы** — такси, доставка еды, курьерские услуги
- ✅ **Парковая самозанятость** — помощь в оформлении нового выгодного статуса
- ✅ **Региональная экспертиза** — знание особенностей каждого региона РФ

### 🏆 Что нас отличает от конкурентов:
> **Первый в России таксопарк с ИИ-агентом, который понимает специфику отрасли и говорит на языке водителей и курьеров**

- **ИИ-помощник** — мгновенные ответы на любые вопросы 24/7
- **Умная аналитика** — прогнозы заработка и оптимальные стратегии работы
- **Автоматизация процессов** — от консультации до подключения за минуты, а не дни
- **Персональный подход** — ИИ запоминает предпочтения и историю каждого клиента

---

## 🤖 ИИ-Агент: Умный помощник таксопарка

### 🧠 Возможности ИИ-агента:

#### **Консультирование и планирование:**
- 📊 **Анализ доходности** — расчет потенциального заработка по регионам и статусам
- 🗺️ **Выбор региона** — рекомендации оптимального города для работы
- 📋 **Подбор статуса** — ИП, самозанятый или парковая самозанятость
- 🚗 **Требования к авто** — проверка соответствия автомобиля требованиям региона
- ⏰ **Планирование графика** — оптимальные часы и дни для максимального заработка

#### **Документооборот и оформление:**
- 📝 **Помощь с заявками** — пошаговое заполнение форм подключения
- ✅ **Проверка документов** — валидация всех необходимых бумаг
- 🏥 **Медосмотры** — поиск ближайших медцентров
- 🚙 **Регистрация авто** — помощь с оформлением в такси
- 💰 **Налоговое планирование** — расчеты по разным статусам

#### **Поддержка и обучение:**
- 🎓 **Обучающие материалы** — персонализированные курсы для новичков
- 🔧 **Решение проблем** — диагностика и решение типичных сложностей
- 📞 **Эскалация в поддержку** — передача сложных случаев специалистам
- 📈 **Анализ эффективности** — советы по увеличению заработка

### 🛠️ Техническая реализация ИИ:

#### **API Конфигурация:**
```python
import os

AI_CONFIG = {
    "apiKey": os.environ.get("OPENROUTER_API_KEY"),  # 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
    "baseURL": 'https://openrouter.ai/api/v1',
    "model": 'google/gemini-2.0-flash-001',
    "maxTokens": 4096,
    "temperature": 0.7
}
```

#### **Интеграция на сайте:**
- 💬 **Чат-виджет с выбором** — плавающий чат в правом нижнем углу
  - 🤖 **ИИ-консультант** — мгновенные ответы на типовые вопросы
  - 👨‍💼 **Живой менеджер** — персональная консультация с экспертом
  - 🔄 **Переключение режимов** — возможность сменить ИИ на человека в любой момент
- 📱 **Мобильная оптимизация** — адаптированный интерфейс для телефонов
- 🔄 **Контекстные диалоги** — ИИ помнит предыдущие сообщения сессии
- ⚡ **Быстрые ответы** — типовые вопросы с готовыми кнопками
- 📲 **Telegram интеграция** — уведомления менеджерам и ответы через бот

#### **Безопасность и приватность:**
- 🔐 **Шифрование данных** — все персональные данные защищены
- 🚫 **Не сохраняем личную информацию** — ИИ работает только с техническими вопросами
- ✅ **GDPR совместимость** — соответствие требованиям защиты данных
- 🛡️ **Rate limiting** — защита от спама и злоупотреблений

---

## 📚 Структура документации

### 🚗 Для водителей
- **[requirements-drivers.md](requirements-drivers.md)** — полные требования для водителей
  - Все варианты статусов (самозанятый, парковая самозанятость, ИП, трудовой договор)
  - Требования к документам для граждан РФ и иностранцев
  - Требования к автомобилям по регионам
  - Медицинские требования и ограничения рабочего времени

### 🚴‍♂️ Для курьеров
- **[requirements-couriers.md](requirements-couriers.md)** — требования для курьеров
  - Типы курьерской работы (пеший, велокурьер, автокурьер)
  - Категории доставки (Яндекс.Еда, Доставка, Лавка)
  - Экипировка и оборудование
  - Заработок и режим работы

### 📋 Процесс подключения
- **[onboarding-process.md](onboarding-process.md)** — пошаговый процесс
  - 7 этапов подключения от заявки до первого заработка
  - Особенности для водителей и курьеров
  - Цифровые инструменты и поддержка
  - Типичные проблемы и их решения

### 🏢 Анализ конкурентов
- **[competitor-analysis.md](competitor-analysis.md)** — детальный анализ
  - Крупнейшие федеральные партнеры (GetDriver, Admiral, Ситимобил Драйв)
  - Региональные таксопарки по городам
  - Конкурентные преимущества ilpo-taxi.top
  - SWOT-анализ и стратегия конкуренции

### ⚖️ Юридические требования
- **[legal-requirements.md](legal-requirements.md)** — правовые аспекты
  - Федеральный закон 580-ФЗ о такси
  - Статусы работников и налогообложение 2025
  - ОСГОП и страховые требования
  - Региональные особенности законодательства

---

## 🎯 Цели документации

### 👥 Для ИИ-агентов:
Эта документация создана специально для **искусственного интеллекта**, который будет разрабатывать проект ilpo-taxi.top с нуля. Каждый файл содержит:

- ✅ **Актуальную информацию** на 2025 год
- ✅ **Практические детали** для реального использования
- ✅ **Структурированные данные** в markdown-формате
- ✅ **Чек-листы и таблицы** для быстрого понимания
- ✅ **Конкурентную аналитику** для правильного позиционирования

### 🔧 Для разработчиков:
- Полное понимание бизнес-логики проекта
- Требования к функциональности сайта
- Понимание целевой аудитории и их потребностей
- Технические требования для интеграций

### 📊 Для маркетологов:
- Анализ конкурентной среды
- Уникальные преимущества для продвижения
- Особенности целевой аудитории
- Региональная специфика для локального маркетинга

---

## 🛠️ Технологические требования

### 🌐 Веб-технологии (обновленные под ИИ):
- **Backend**: FastAPI (Python 3.9+) с поддержкой async/await
- **База данных**: PostgreSQL 14 для данных и логов
- **Кэширование**: Redis для сессий и часто задаваемых вопросов
- **Frontend**: HTML5, CSS3, JavaScript ES6+ для чат-интерфейса
- **Фреймворки**: Bootstrap 5, Vanilla JS (без jQuery)
- **ИИ-интеграция**: OpenRouter API (Gemini 2.0 Flash)
- **Telegram Bot**: Python + aiogram для живых менеджеров
- **Веб-сервер**: Nginx (stable) как reverse proxy
- **VPS**: Ubuntu 22.04 LTS на jino.ru

### 🤖 ИИ-инфраструктура:
- ✅ **OpenRouter API** — интеграция с Gemini 2.0 Flash через FastAPI
- ✅ **PostgreSQL** — хранение диалогов и пользовательских данных
- ✅ **Redis** — кэширование ответов ИИ и сессий чата
- ✅ **aiogram** — современный фреймворк для Telegram бота
- ✅ **Nginx** — балансировка нагрузки и SSL терминация
- ✅ **Gunicorn + Uvicorn** — production-ready ASGI сервер

### 📱 Адаптивность:
- ✅ Мобильная версия (50%+ трафика с мобильных)
- ✅ Планшетная версия
- ✅ Десктопная версия
- ✅ **ИИ-чат адаптирован под все устройства**

### 🔗 Интеграции:
- ✅ **OpenRouter API** — ИИ-консультант на базе Gemini 2.0 Flash
- ✅ **Telegram Bot (aiogram)** — двусторонняя связь с менеджерами
  - 📨 **Уведомления**: сообщения с чат-виджета → Telegram
  - 📩 **Ответы**: Telegram → чат-виджет на сайте  
  - 🔄 **Синхронизация**: real-time обмен через PostgreSQL + Redis
- ✅ **WebSocket** — мгновенная доставка ответов менеджеров
- ✅ **PostgreSQL** — хранение всех диалогов и пользовательских данных
- ✅ **Redis** — кэширование, сессии и pub/sub для real-time
- ✅ **Аналитика** — Яндекс.Метрика + ИИ-аналитика диалогов

---

## 📈 Ключевые выводы исследования

### 💡 Рыночные инсайты:

#### **1. Парковая самозанятость — новый тренд 2025:**
- Максимальные льготы и приоритеты от Яндекс.Такси
- Сочетание низких налогов (4-6%) с официальным доходом
- Большинство водителей пока не знают о новых возможностях

#### **2. Конкуренция среди партнеров, а не агрегаторов:**
- Основные конкуренты — GetDriver, Admiral, региональные таксопарки
- Проблема: обезличенный сервис, сложные процедуры
- Возможность: персональный подход и экспертиза

#### **3. Региональная специфика критична:**
- Москва: только желтые авто, жесткие требования
- Регионы: более лояльные условия, но меньше информации
- Необходимость локальной экспертизы по каждому региону

#### **4. Растущие требования к документообороту:**
- 580-ФЗ усложнил процедуры подключения
- ОСГОП стал обязательным с 2024 года
- Водители нуждаются в помощи юристов

### 🎯 Позиционирование ilpo-taxi.top:

> **"Первый Умный Таксопарк России с ИИ-помощником"**
> 
> Революционный подход к подключению водителей и курьеров. Наш ИИ-агент работает 24/7, мгновенно отвечает на любые вопросы, помогает выбрать оптимальный статус работы и прогнозирует заработок. Превращаем сложный процесс подключения в простой диалог с умным помощником.

#### **Уникальные преимущества ИИ-интеграции:**
- 🕒 **24/7 доступность** — консультации в любое время
- ⚡ **Мгновенные ответы** — не нужно ждать консультанта
- 🧠 **Накопление знаний** — ИИ становится умнее с каждым диалогом
- 📊 **Персонализация** — индивидуальные рекомендации для каждого
- 🎯 **Высокая точность** — специализация на таксомоторной отрасли

---

## 📞 Рекомендации по использованию

### 🤖 Для ИИ-разработчиков:
1. **Изучите всю документацию** — особенно требования к водителям и курьерам
2. **Интегрируйте OpenRouter API** — используйте предоставленные ключи безопасно
3. **Создайте контекстную базу знаний** — ИИ должен знать специфику отрасли
4. **Предусмотрите эскалацию** — сложные случаи передавайте людям
5. **Оптимизируйте под мобильные** — большинство пользователей на телефонах

### 👨‍💻 Для разработчиков:
1. **VPS сервер Ubuntu 22.04** — развертывание на jino.ru
2. **FastAPI + Gunicorn + Nginx** — production-ready архитектура
3. **PostgreSQL 14** — надежное хранение всех данных
4. **Redis** — кэширование и pub/sub для real-time
5. **aiogram** — современный Telegram бот на Python
6. **Безопасность** — переменные окружения для всех ключей

### 📊 Для маркетологов:
1. **ИИ как главное преимущество** — первый умный таксопарк в России
2. **Демонстрация возможностей** — видео с примерами диалогов
3. **SEO под ИИ-запросы** — "умный таксопарк", "ИИ помощник водителя"
4. **Партнерства с ИИ-компаниями** — техническая экспертиза как преимущество
5. **Кейсы и отзывы** — истории успеха с ИИ-помощником

---

## 🔧 Техническая реализация ИИ-агента

### 📋 Требования к разработке:

#### **Backend (FastAPI + Python):**
```python
# main.py - FastAPI приложение
from fastapi import FastAPI, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncpg
import aioredis
import httpx
import os
from typing import Optional

app = FastAPI(title="ilpo-taxi.top API")

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Конфигурация
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-...")
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/ilpo_taxi")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class ChatHandler:
    def __init__(self):
        self.ai_assistant = AIAssistant()
        self.telegram_bot = TelegramBot()
    
    async def handle_message(self, session_id: str, message: str, mode: str = 'ai'):
        if mode == 'ai':
            return await self.ai_assistant.send_message(message, session_id)
        else:
            return await self.telegram_bot.forward_to_manager(session_id, message)

class AIAssistant:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = 'https://openrouter.ai/api/v1'
        self.model = 'google/gemini-2.0-flash-001'
    
    async def send_message(self, user_message: str, session_id: str):
        # Проверяем кэш в Redis
        redis = await aioredis.from_url(REDIS_URL)
        cached_response = await redis.get(f"ai_cache:{hash(user_message)}")
        
        if cached_response:
            return cached_response.decode()
        
        # Отправляем запрос к OpenRouter API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": user_message}],
                    "max_tokens": 4096,
                    "temperature": 0.7
                }
            )
            
        ai_response = response.json()["choices"][0]["message"]["content"]
        
        # Кэшируем ответ
        await redis.setex(f"ai_cache:{hash(user_message)}", 3600, ai_response)
        
        # Логируем в PostgreSQL
        await self.log_dialog(session_id, user_message, ai_response)
        
        return ai_response
    
    async def log_dialog(self, session_id: str, user_msg: str, ai_msg: str):
        conn = await asyncpg.connect(POSTGRES_URL)
        await conn.execute("""
            INSERT INTO chat_logs (session_id, user_message, ai_response, created_at)
            VALUES ($1, $2, $3, NOW())
        """, session_id, user_msg, ai_msg)
        await conn.close()

# API эндпоинты
@app.post("/api/chat")
async def chat_endpoint(request: dict):
    handler = ChatHandler()
    response = await handler.handle_message(
        request["session_id"], 
        request["message"], 
        request.get("mode", "ai")
    )
    return {"response": response}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    # WebSocket для real-time обмена с менеджерами
    while True:
        data = await websocket.receive_text()
        # Обработка сообщений через Redis pub/sub
        await websocket.send_text(f"Echo: {data}")

@app.get("/")
async def read_root():
    # Возвращаем главную страницу
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
```

#### **Telegram Bot (Python + aiogram):**
```python
# telegram_bot.py - Telegram бот для менеджеров
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncpg
import aioredis

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POSTGRES_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class TelegramBot:
    def __init__(self):
        self.bot = bot
        self.manager_chat_ids = []  # ID чатов менеджеров
    
    async def forward_to_manager(self, session_id: str, message: str, user_info: dict = None):
        """Отправка сообщения с сайта менеджерам в Telegram"""
        text = f"🔔 НОВОЕ СООБЩЕНИЕ С САЙТА\n\n"
        text += f"📱 Сессия: #{session_id}\n"
        if user_info:
            text += f"👤 Имя: {user_info.get('name', 'Не указано')}\n"
            text += f"📞 Телефон: {user_info.get('phone', 'Не указан')}\n"
        text += f"🕐 Время: {datetime.now().strftime('%H:%M, %d.%m.%Y')}\n\n"
        text += f"💬 Сообщение:\n{message}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"✍️ Для ответа используйте:\n/reply {session_id} Ваш ответ"
        
        for chat_id in self.manager_chat_ids:
            await self.bot.send_message(chat_id, text)
    
    async def send_to_website(self, session_id: str, response: str):
        """Отправка ответа менеджера обратно на сайт через Redis"""
        redis = await aioredis.from_url(REDIS_URL)
        await redis.publish(f"manager_response:{session_id}", response)

# Обработчики команд бота
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("""
🤖 Добро пожаловать в бот менеджеров ilpo-taxi.top!

📋 Доступные команды:
/active - список активных диалогов
/reply <session_id> <текст> - ответить клиенту
/close <session_id> - завершить диалог

🔔 Вы будете получать уведомления о новых сообщениях с сайта.
    """)

@dp.message(Command("reply"))
async def cmd_reply(message: Message):
    """Ответ клиенту на сайте"""
    try:
        args = message.text.split(' ', 2)
        if len(args) < 3:
            await message.answer("❌ Неверный формат. Используйте: /reply <session_id> <текст>")
            return
        
        session_id = args[1]
        response_text = args[2]
        
        # Отправляем ответ на сайт через Redis
        telegram_bot = TelegramBot()
        await telegram_bot.send_to_website(session_id, response_text)
        
        # Логируем в базу
        conn = await asyncpg.connect(POSTGRES_URL)
        await conn.execute("""
            INSERT INTO chat_logs (session_id, manager_response, created_at)
            VALUES ($1, $2, NOW())
        """, session_id, response_text)
        await conn.close()
        
        await message.answer(f"✅ Ответ отправлен клиенту (сессия #{session_id})")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("active"))
async def cmd_active(message: Message):
    """Список активных диалогов"""
    conn = await asyncpg.connect(POSTGRES_URL)
    active_sessions = await conn.fetch("""
        SELECT DISTINCT session_id, MAX(created_at) as last_activity
        FROM chat_logs 
        WHERE created_at > NOW() - INTERVAL '1 hour'
        GROUP BY session_id
        ORDER BY last_activity DESC
    """)
    await conn.close()
    
    if not active_sessions:
        await message.answer("📭 Нет активных диалогов")
        return
    
    text = "📋 Активные диалоги:\n\n"
    for session in active_sessions:
        text += f"📱 #{session['session_id']} - {session['last_activity'].strftime('%H:%M')}\n"
    
    await message.answer(text)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
```

#### **База знаний ИИ:**
- 📚 **Все документы из docs/** — полная информация о требованиях
- 🗺️ **Региональные особенности** — данные по всем городам России
- 💰 **Калькуляторы заработка** — формулы расчета дохода
- 📋 **Чек-листы подключения** — пошаговые инструкции
- ❓ **FAQ база** — часто задаваемые вопросы и ответы

#### **Архитектура чат-виджета:**

##### **1. Инициализация виджета:**
```javascript
// При загрузке страницы показывается выбор режима
<div class="chat-widget">
  <div class="mode-selector">
    <h4>💬 Выберите тип консультации:</h4>
    <button class="ai-mode">🤖 ИИ-консультант (мгновенно)</button>
    <button class="human-mode">👨‍💼 Живой менеджер (персонально)</button>
  </div>
</div>
```

##### **2. Режим ИИ-консультанта:**
- Пользователь выбирает "ИИ-консультант"
- Сообщения отправляются на `/api/ai-chat`
- Ответы приходят от OpenRouter API (Gemini 2.0 Flash)
- В любой момент доступна кнопка "Связаться с менеджером"

##### **3. Режим живого менеджера:**
```mermaid
graph TD
    A[Пользователь выбирает "Живой менеджер"] --> B[Показ формы: имя, телефон, вопрос]
    B --> C[Отправка данных в Telegram бот]
    C --> D[Уведомление менеджеру в Telegram]
    D --> E[Менеджер отвечает: /reply sessionId текст]
    E --> F[Ответ появляется в чат-виджете]
    F --> G[Продолжение диалога через Telegram ↔ Сайт]
```

##### **4. Telegram бот для менеджеров:**
**Команды бота:**
- `/start` — приветствие и инструкции
- `/active` — список активных диалогов
- `/reply {sessionId} {текст}` — ответ пользователю на сайте
- `/close {sessionId}` — завершение диалога

**Пример уведомления:**
```
🔔 НОВЫЙ ДИАЛОГ С САЙТА

📱 Сессия: #12345
👤 Имя: Иван Петров  
📞 Телефон: +7 900 123-45-67
🕐 Время: 15:30, 25.01.2025

💬 Вопрос:
"Хочу стать водителем в Москве. У меня Kia Rio 2020 года, подойдет ли для такси?"

━━━━━━━━━━━━━━━━━━━━
✍️ Для ответа используйте:
/reply 12345 Ваш ответ клиенту
```

##### **5. Real-time синхронизация:**
- **WebSocket** или **Server-Sent Events** для мгновенной доставки
- Пользователь видит статус: "Менеджер печатает..."
- Показ времени последней активности менеджера
- Уведомление о подключении/отключении менеджера

### 🎯 Ключевые сценарии использования:

#### **ИИ-консультант (автоматический режим):**
1. **"Хочу стать водителем такси"**
   - ИИ узнает регион, наличие авто, статус
   - Предлагает оптимальный путь подключения
   - Рассчитывает потенциальный заработок

2. **"Подойдет ли мой автомобиль?"**
   - ИИ запрашивает марку, модель, год, регион
   - Проверяет соответствие требованиям
   - Предлагает альтернативы при несоответствии

3. **"Сколько буду зарабатывать?"**
   - ИИ учитывает регион, график, опыт
   - Показывает реалистичные цифры
   - Сравнивает разные статусы работы

#### **Живой менеджер (персональный режим):**
1. **Процесс подключения живого менеджера:**
   ```
   Пользователь → Выбирает "Живой менеджер" → 
   Сообщение отправляется в Telegram бот → 
   Менеджер получает уведомление → 
   Менеджер отвечает в боте → 
   Ответ появляется в чат-виджете
   ```

2. **Telegram бот для менеджеров:**
   - 🔔 **Уведомления**: "Новое сообщение с сайта"
   - 📱 **Информация о сессии**: ID пользователя, время
   - 💬 **Текст сообщения**: полное сообщение клиента
   - ✍️ **Ответ**: `/reply {sessionId} Ваш ответ клиенту`

3. **Переключение режимов:**
   - Пользователь может сменить ИИ на человека в любой момент
   - ИИ автоматически предлагает живого менеджера при сложных вопросах
   - История диалога передается менеджеру для контекста

---

## 🚀 Развертывание на VPS Ubuntu 22.04

### 📋 Системные требования:
- **Сервер**: Ubuntu 22.04 LTS на jino.ru
- **Python**: 3.9+ с pip
- **База данных**: PostgreSQL 14
- **Кэширование**: Redis 6+
- **Веб-сервер**: Nginx (stable)
- **Процессор**: 2+ ядра
- **RAM**: 2GB+ (рекомендуется 4GB)
- **Диск**: 20GB+ SSD

### 🛠️ Пошаговая установка:

#### **1. Обновление системы:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install software-properties-common curl wget git -y
```

#### **2. Установка Python 3.9+:**
```bash
sudo apt install python3 python3-pip python3-venv python3-dev -y
python3 --version  # Проверка версии
```

#### **3. Установка PostgreSQL 14:**
```bash
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создание базы данных
sudo -u postgres psql
CREATE DATABASE ilpo_taxi;
CREATE USER ilpo_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE ilpo_taxi TO ilpo_user;
\q
```

#### **4. Установка Redis:**
```bash
sudo apt install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping  # Должен вернуть PONG
```

#### **5. Установка Nginx:**
```bash
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### **6. Клонирование и настройка проекта:**
```bash
cd /var/www
sudo git clone https://github.com/your-repo/ilpo-taxi.top.git
sudo chown -R $USER:$USER /var/www/ilpo-taxi.top
cd /var/www/ilpo-taxi.top

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install fastapi uvicorn gunicorn
pip install asyncpg aioredis httpx
pip install aiogram  # Для Telegram бота
```

#### **7. Конфигурация переменных окружения:**
```bash
# Создание .env файла
cat > .env << EOF
# OpenRouter API
OPENROUTER_API_KEY=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

# База данных
DATABASE_URL=postgresql://ilpo_user:secure_password_here@localhost/ilpo_taxi

# Redis
REDIS_URL=redis://localhost:6379

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# FastAPI
FASTAPI_ENV=production
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
EOF

chmod 600 .env  # Ограничение доступа к файлу
```

#### **8. Создание systemd сервисов:**

**FastAPI сервис:**
```bash
sudo tee /etc/systemd/system/ilpo-fastapi.service > /dev/null << EOF
[Unit]
Description=ilpo-taxi.top FastAPI
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=/var/www/ilpo-taxi.top
Environment=PATH=/var/www/ilpo-taxi.top/venv/bin
EnvironmentFile=/var/www/ilpo-taxi.top/.env
ExecStart=/var/www/ilpo-taxi.top/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

**Telegram Bot сервис:**
```bash
sudo tee /etc/systemd/system/ilpo-telegram-bot.service > /dev/null << EOF
[Unit]
Description=ilpo-taxi.top Telegram Bot
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=/var/www/ilpo-taxi.top
Environment=PATH=/var/www/ilpo-taxi.top/venv/bin
EnvironmentFile=/var/www/ilpo-taxi.top/.env
ExecStart=/var/www/ilpo-taxi.top/venv/bin/python telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

#### **9. Конфигурация Gunicorn:**
```bash
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
EOF
```

#### **10. Конфигурация Nginx:**
```bash
sudo tee /etc/nginx/sites-available/ilpo-taxi.top > /dev/null << EOF
server {
    listen 80;
    server_name ilpo-taxi.top www.ilpo-taxi.top;
    
    client_max_body_size 10M;
    
    # Статические файлы
    location /static/ {
        alias /var/www/ilpo-taxi.top/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # WebSocket соединения
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # API и основное приложение
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/ilpo-taxi.top /etc/nginx/sites-enabled/
sudo nginx -t  # Проверка конфигурации
sudo systemctl reload nginx
```

#### **11. Инициализация базы данных:**
```python
# create_tables.py
import asyncio
import asyncpg
import os

async def create_tables():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    # Таблица для логов чата
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            user_message TEXT,
            ai_response TEXT,
            manager_response TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            INDEX (session_id, created_at)
        );
    """)
    
    # Таблица для пользователей (опционально)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE,
            name VARCHAR(255),
            phone VARCHAR(20),
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    await conn.close()
    print("✅ Таблицы созданы успешно!")

if __name__ == "__main__":
    asyncio.run(create_tables())
```

#### **12. Запуск сервисов:**
```bash
# Инициализация базы данных
source venv/bin/activate
python create_tables.py

# Запуск и автозагрузка сервисов
sudo systemctl daemon-reload
sudo systemctl start ilpo-fastapi
sudo systemctl start ilpo-telegram-bot
sudo systemctl enable ilpo-fastapi
sudo systemctl enable ilpo-telegram-bot

# Проверка статуса
sudo systemctl status ilpo-fastapi
sudo systemctl status ilpo-telegram-bot
```

#### **13. SSL сертификат (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d ilpo-taxi.top -d www.ilpo-taxi.top

# Автообновление сертификата
sudo crontab -e
# Добавить строку:
0 12 * * * /usr/bin/certbot renew --quiet
```

### 🔧 Мониторинг и логи:

#### **Просмотр логов:**
```bash
# Логи FastAPI
sudo journalctl -u ilpo-fastapi -f

# Логи Telegram бота
sudo journalctl -u ilpo-telegram-bot -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### **Перезапуск сервисов:**
```bash
# При изменении кода
sudo systemctl restart ilpo-fastapi
sudo systemctl restart ilpo-telegram-bot

# При изменении конфигурации Nginx
sudo nginx -t && sudo systemctl reload nginx
```

### 📊 Структура файлов проекта:
```
/var/www/ilpo-taxi.top/
├── main.py                 # FastAPI приложение
├── telegram_bot.py         # Telegram бот
├── gunicorn.conf.py        # Конфигурация Gunicorn
├── create_tables.py        # Инициализация БД
├── .env                    # Переменные окружения
├── requirements.txt        # Python зависимости
├── static/                 # Статические файлы
│   ├── index.html         # Главная страница
│   ├── css/               # Стили
│   ├── js/                # JavaScript
│   └── images/            # Изображения
└── venv/                  # Виртуальное окружение
```

---

## 📅 Актуальность информации

**Последнее обновление**: Январь 2025 года (+ добавлена ИИ-интеграция)

**Источники данных**:
- ✅ Официальные сайты Яндекс.Такси и Яндекс.Про
- ✅ Федеральный закон 580-ФЗ и подзаконные акты
- ✅ Исследование конкурентов (GetDriver, Admiral и др.)
- ✅ **OpenRouter API документация** — техническая интеграция ИИ
- ✅ **Gemini 2.0 Flash** — возможности и ограничения модели

**⚠️ Важно**: ИИ-технологии развиваются стремительно. Рекомендуется регулярно обновлять промпты и базу знаний агента для повышения качества ответов.

---

🚀 **Готовы создать первый Умный Таксопарк России с ИИ-агентом? Все техническое решение и бизнес-логика описаны в этой документации!** 🤖 