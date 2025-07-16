"""
OpenRouter AI Service - Интеграция с OpenRouter API
Умный ИИ-консультант для ILPO-TAXI таксопарка
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import re

class OpenRouterAI:
    """Сервис для работы с OpenRouter API"""
    
    def __init__(self):
        # Используем разные ключи и модели для разных задач
        self.api_key_consultant = os.getenv("OPENROUTER_API_KEY_CONSULTANT")
        self.api_key_search = os.getenv("OPENROUTER_API_KEY_SEARCH") 
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        
        # Основная модель (дешевая) для консультирования
        self.model_consultant = os.getenv("OPENROUTER_MODEL_CONSULTANT", "google/gemini-2.0-flash-001")
        # Поисковая модель (дорогая) только для веб-поиска
        self.model_search = os.getenv("OPENROUTER_MODEL_SEARCH", "openai/gpt-4o-mini-search-preview")
        
        self.site_url = os.getenv("SITE_URL", "https://ilpo-taxi.top")
        self.site_name = os.getenv("SITE_NAME", "ILPO-TAXI Smart Taxi")

        print(f"DEBUG: OPENROUTER_API_KEY_CONSULTANT = {os.getenv('OPENROUTER_API_KEY_CONSULTANT')}")

        if not self.api_key_consultant:
            raise ValueError("OPENROUTER_API_KEY_CONSULTANT не найден в переменных окружения")
        if not self.api_key_search:
            raise ValueError("OPENROUTER_API_KEY_SEARCH не найден в переменных окружения")
        
        # Создаем HTTP клиенты для разных задач с правильными ключами
        self.client_consultant = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key_consultant}",
                "HTTP-Referer": self.site_url,
                "X-Title": self.site_name,
                "Content-Type": "application/json"
            }
        )
        
        self.client_search = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key_search}",
                "HTTP-Referer": self.site_url,
                "X-Title": self.site_name,
                "Content-Type": "application/json"
            }
        )
    
    async def close(self):
        """Закрыть HTTP клиенты"""
        await self.client_consultant.aclose()
        await self.client_search.aclose()
    
    def get_system_prompt(self) -> str:
        """Возвращает системный промпт для ИИ-консультанта ILPO-TAXI"""
        return """Ты - ИИ-консультант ILPO-TAXI, первого в России умного таксопарка. Твоя задача - помочь водителям и курьерам подключиться ТОЛЬКО к ILPO-TAXI.

ОГРАНИЧЕНИЯ НА ОТВЕТЫ:
• Максимум 1500 токенов на ответ
• При поиске - максимум 5 вариантов
• Отвечай кратко и по делу
• Избегай длинных текстов и повторений
• Структурируй ответы списками для краткости

СТРОГО ЗАПРЕЩЕНО:
• Упоминать другие таксопарки! (IMPERATOR, R-City, Гутенпарк, Максим, Везет, Сити Мобил и т.д.)
• Давать ссылки на конкурентов
• Советовать обращаться к другим компаниям

КЛЮЧЕВАЯ ИНФОРМАЦИЯ ILPO-TAXI:
• Таксопарк с самой низкой комиссией в России (1,5-7%)
• Подключение за 24 часа для водителей, 2-4 часа для курьеров
• Круглосуточная поддержка
• Собственный автопарк в аренду от 1200₽/сутки (если пользователь с Пензы)
• Офис: г. Пенза, ул. Калинина 128А к2

УСЛУГИ ТОЛЬКО ILPO-TAXI:
1. Подключение к Яндекс.Такси (водители)
2. Подключение к Яндекс.Доставке (курьеры)
3. Грузовые перевозки (водители с грузовым транспортом)
4. Аренда автомобилей (только для Пензы)
5. Полная поддержка и обучение

ТРЕБОВАНИЯ ДЛЯ ВОДИТЕЛЕЙ:
• Возраст от 21 года
• Стаж вождения от 3 лет
• Паспорт РФ
• Водительское удостоверение
• СТС

ТРЕБОВАНИЯ ДЛЯ КУРЬЕРОВ:
• Возраст от 18 лет
• Паспорт РФ
• Справка о несудимости
• Собственный транспорт (авто, мото, велосипед, пешком)

ЗАРАБОТОК С ILPO-TAXI:
• Водители: 80-120 тысяч рублей в месяц
• Курьеры: 50-80 тысяч рублей в месяц
• Грузовые перевозки: 100-150 тысяч рублей в месяц
• Водители получают 93-98,5% от стоимости поездки
• Ежедневные выплаты

СТИЛЬ ОБЩЕНИЯ И ОТВЕТОВ:
• Дружелюбный и профессиональный
• Используй эмодзи умеренно
• Отвечай кратко и конкретно (максимум 1500 токенов!)
• Предлагай следующие шаги
• Мотивируй к подключению ТОЛЬКО к ILPO-TAXI
• При поиске - показывай максимум 5 самых релевантных вариантов
• Структурируй ответы списками для краткости

ВАЖНО: Всегда предлагай заполнить форму заявки по ссылке <a href="/signup">/signup</a> или связаться с менеджером ILPO-TAXI по номеру <a href="tel:+79968073743">+7 996 807-37-43</a> для быстрого подключения.

ПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:
"Привет! 🚕 Рад, что ты хочешь работать с ILPO-TAXI!

**Требования для водителей:**
• От 21 года, стаж от 3 лет
• Паспорт, права, СТС

**Наши преимущества:**
• Комиссия 1,5-7% (самая низкая в России!)
• Заработок 80-120 тысяч/месяц
• Подключение за 24 часа

**Как начать:**
1. Заявка: <a href="/signup">/signup</a>
2. Звонок менеджера через 30 мин
3. Подготовка документов
4. Работа через 24 часа!

Связаться сейчас: <a href="tel:+79968073743">+7 996 807-37-43</a> 👍"

НОВЫЕ ПРАВИЛА:
• Упоминай о нашем офисе (г. Пенза, ул. Калинина 128А к2) ТОЛЬКО если пользователь явно спрашивает об адресе или местоположении офиса.
• Упоминай о возможности аренды автомобилей (от 1200₽/сутки) ТОЛЬКО если пользователь указывает, что он из Пензы или Пензенской области или спрашивает про аренду автомобиля.

КРИТИЧЕСКИ ВАЖНО: НИКОГДА не упоминай, не рекомендуй и не давай контакты других таксопарков. Ты работаешь ТОЛЬКО для ILPO-TAXI!"""

    async def generate_response(self, user_message: str, conversation_history: List[Dict] = None, use_web_search: bool = True) -> str:
        """
        Генерирует ответ ИИ на сообщение пользователя
        
        Args:
            user_message: Сообщение пользователя
            conversation_history: История разговора
            use_web_search: Использовать ли веб-поиск
            
        Returns:
            Ответ ИИ
        """
        try:
            # Определяем, нужен ли веб-поиск для критической информации
            needs_web_search = use_web_search and self.should_use_web_search(user_message)
            
            # Выбираем модель и клиент в зависимости от необходимости поиска
            if needs_web_search:
                model = self.model_search
                client = self.client_search
                print(f"🔍 Используется поисковая модель: {model}")
            else:
                model = self.model_consultant
                client = self.client_consultant
                print(f"💬 Используется консультативная модель: {model}")
            
            # Формируем сообщения для API
            messages = [
                {"role": "system", "content": self.get_system_prompt()}
            ]
            
            # Добавляем историю разговора если есть
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Последние 10 сообщений
            
            # Добавляем текущее сообщение пользователя
            messages.append({"role": "user", "content": user_message})
            
            # Формируем запрос к OpenRouter API
            # Ограничиваем токены для краткости ответов
            max_tokens = 1500 if needs_web_search else 1000
            
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False
            }
            
            # Модифицируем запрос для активации веб-поиска только для критических случаев
            if needs_web_search:
                original_message = messages[-1]["content"]
                enhanced_message = f"{original_message}\n\n🔍 **ИНСТРУКЦИИ ДЛЯ ВЕБ-ПОИСКА:**\n\n❌ **СТРОГО ЗАПРЕЩЕНО:**\n• Более 5 результатов\n• Повторяющиеся организации\n• Упоминать конкурентские таксопарки\n• Длинные списки\n\n✅ **ОБЯЗАТЕЛЬНО:**\n• Только 5 лучших мест\n• Краткая информация: название, адрес, телефон\n• В конце предложить ILPO-TAXI\n• Максимум 1500 токенов\n\n📋 **ФОРМАТ ОТВЕТА:**\n```\nПривет! Вот 5 лучших мест для получения медкнижки в Пензе:\n\n1. [Название] - [адрес], тел: [телефон]\n2. [Название] - [адрес], тел: [телефон]\n3. [Название] - [адрес], тел: [телефон]\n4. [Название] - [адрес], тел: [телефон]\n5. [Название] - [адрес], тел: [телефон]\n\n**Для работы в ILPO-TAXI звоните:** +7 996 807-37-43\n```"
                messages[-1]["content"] = enhanced_message
                print(f"🔍 Включен веб-поиск для запроса: {user_message[:500]}...")
            
            # Отправляем запрос
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                # Если использовался веб-поиск, применяем жесткие ограничения
                if needs_web_search:
                    ai_response = self.limit_search_results(ai_response)
                
                # Дополнительная проверка длины ответа
                max_chars = 8000  # Примерно 1500-2000 токенов
                if len(ai_response) > max_chars:
                    # Обрезаем ответ и добавляем примечание
                    ai_response = ai_response[:max_chars].rsplit(' ', 1)[0] + "...\n\n💬 [Ответ сокращен для краткости. Задайте уточняющий вопрос для получения дополнительной информации.]"
                    print(f"✂️ Ответ обрезан до {len(ai_response)} символов")
                
                print(f"✅ OpenRouter API успешно: {len(ai_response)} символов")
                print(f"📝 Полный ответ ИИ:\n{ai_response}") # Полный вывод без обрезания
                return ai_response
            else:
                print(f"❌ Ошибка OpenRouter API: {response.status_code} - {response.text}")
                return self.get_fallback_response(user_message)
                
        except Exception as e:
            print(f"❌ Исключение в OpenRouter AI: {e}")
            return self.get_fallback_response(user_message)
    
    def get_fallback_response(self, user_message: str) -> str:
        """Резервные ответы когда API недоступен"""
        
        user_message_lower = user_message.lower()
        
        # Интеллектуальные резервные ответы только про ILPO-TAXI
        if any(word in user_message_lower for word in ['привет', 'здравствуй', 'добро']):
            return "Привет! 👋 Я ИИ-консультант ILPO-TAXI. Помогу подключиться к Яндекс.Такси или Доставке через наш таксопарк. Что вас интересует - работа водителем, курьером или и то и другое?"
        
        elif any(word in user_message_lower for word in ['документы', 'нужно', 'требования']):
            return "📋 Для водителей нужны: паспорт, права, СТС, диагностическая карта. Для курьеров: паспорт, справка о несудимости. Подключение к ILPO-TAXI за 24 часа!"
        
        elif any(word in user_message_lower for word in ['заработок', 'деньги', 'зарплата', 'доход']):
            return "💰 С ILPO-TAXI водители зарабатывают 80-120 тысяч, курьеры 50-80 тысяч рублей в месяц. Наша комиссия всего 1,5-7% - одна из самых низких в России!"
        
        elif any(word in user_message_lower for word in ['подключ', 'регистр', 'оформ']):
            return "🚀 Подключение к ILPO-TAXI очень быстрое! Водители - 24 часа, курьеры - 2-4 часа. Заполните заявку по ссылке <a href='/signup'>/signup</a> или свяжитесь с менеджером <a href='tel:+79968073743'>+7 996 807-37-43</a>!"
        
        elif any(word in user_message_lower for word in ['машина', 'авто', 'аренда']):
            return "🚗 Можете работать на своем авто или взять в аренду через ILPO-TAXI от 1200₽/сутки (для Пензы). У нас большой автопарк с лицензией такси!"
        
        elif any(word in user_message_lower for word in ['график', 'время', 'смена']):
            return "⏰ С ILPO-TAXI график работы свободный! Работайте когда удобно. Многие выбирают 8-12 часов в день, 5-6 дней в неделю."
        
        elif any(word in user_message_lower for word in ['курьер', 'доставка', 'еда']):
            return "🛵 Отличный выбор! Курьеры с ILPO-TAXI зарабатывают 50-80 тысяч в месяц. Подключение за 2-4 часа, можно работать пешком, на велосипеде или авто!"
        
        elif any(word in user_message_lower for word in ['груз', 'грузовик', 'фура', 'камаз']):
            return "🚛 Грузовые перевозки с ILPO-TAXI - это высокий заработок 100-150 тысяч в месяц! Работайте с любым типом груза и грузоподъемностью. Заполните заявку по ссылке <a href='/signup'>/signup</a>!"
        
        else:
            return "🤖 Сейчас у меня технические неполадки, но я все равно помогу! Спрашивайте о документах, заработке, условиях работы или подключении к ILPO-TAXI. Что интересует больше всего?"

    async def get_smart_response(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Получить умный ответ с дополнительной информацией
        
        Args:
            user_message: Сообщение пользователя
            context: Дополнительный контекст (user_id, session_id и т.д.)
            
        Returns:
            Словарь с ответом и метаданными
        """
        
        start_time = datetime.now()
        
        # Определяем, нужен ли веб-поиск
        needs_web_search = self.should_use_web_search(user_message)
        
        # Получаем ответ от ИИ
        conversation_history = context.get('conversation_history', []) if context else []
        ai_response = await self.generate_response(user_message, conversation_history, use_web_search=needs_web_search)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Определяем интент пользователя
        intent = self.detect_intent(user_message)
        
        # Определяем использованную модель
        used_model = self.model_search if needs_web_search else self.model_consultant
        
        # Формируем результат
        result = {
            "content": ai_response,
            "intent": intent,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "model": used_model,
            "web_search_used": needs_web_search,
            "context": context or {}
        }
        
        print(f"🧠 Умный ответ: {intent} за {processing_time:.2f}с, модель: {used_model}")
        
        return result
    
    def should_use_web_search(self, message: str) -> bool:
        """Определяет, нужно ли использовать веб-поиск для ответа"""
        
        message_lower = message.lower()
        
        # Ключевые слова, указывающие на необходимость актуальной информации
        web_search_indicators = [
            # Географические запросы
            "где", "адрес", "находится", "местонахождение", "как добраться",
            # Медицинские услуги и документы
            "медкнижка", "медкнижку", "медицинская книжка", "справка", "медицинская справка", "Медсправка", "анализы",
            "поликлиника", "больница", "медцентр", "клиника",
            # Административные услуги  
            "мфц", "госуслуги", "паспорт",
            # Актуальная информация
            "сейчас", "сегодня", "текущий", "последний", "новый", "цена", "стоимость",
            # Время и расписание
            "расписание", "часы работы", "время работы", "график",
            # Контакты и телефоны
            "телефон", "номер", "контакт", "связаться",
            # Конкретные города и районы
            "пенза", "пензе", "терновка", "терновке", "район", "городе", "области"
        ]
        
        return any(indicator in message_lower for indicator in web_search_indicators)
    
    def detect_intent(self, message: str) -> str:
        """Определение намерения пользователя"""
        
        message_lower = message.lower()
        
        intent_keywords = {
            "greeting": ["привет", "здравствуй", "добро", "хай", "hey"],
            "documents": ["документы", "справки", "нужно", "требования", "паспорт", "права"],
            "earnings": ["заработок", "деньги", "зарплата", "доход", "сколько", "платят"],
            "connection": ["подключ", "регистр", "оформ", "заявка", "начать"],
            "car_rental": ["машина", "авто", "аренда", "автопарк", "тачка"],
            "schedule": ["график", "время", "смена", "работать", "часы"],
            "courier": ["курьер", "доставка", "еда", "пешком", "велосипед"],
            "taxi": ["водитель", "такси", "машина", "поездка"],
            "commission": ["комиссия", "процент", "забирает", "остается"],
            "support": ["помощь", "поддержка", "вопрос", "проблема"],
            "web_search": ["где", "адрес", "медкнижка", "поликлиника", "мфц", "телефон"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return "general"

    def limit_search_results(self, text: str) -> str:
        """
        Ограничивает количество найденных результатов поиска до 5 и удаляет дубликаты.
        """
        lines = text.split('\n')
        result_lines = []
        found_results = []
        result_count = 0
        
        for line in lines:
            # Если это строка с номером результата (1., 2., 3. и т.д.)
            if re.match(r'^\d+\.', line.strip()) and result_count < 5:
                # Проверяем, не дублируется ли этот результат
                line_text = re.sub(r'^\d+\.\s*', '', line.strip()).lower()
                
                # Проверяем на дубликаты по названию организации
                is_duplicate = False
                for existing in found_results:
                    if line_text in existing or existing in line_text:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    found_results.append(line_text)
                    result_count += 1
                    result_lines.append(line)
                    
                    # Добавляем следующие строки, относящиеся к этому результату
                    continue
            
            # Если мы уже набрали 5 результатов, добавляем только общую информацию
            elif result_count >= 5 and not re.match(r'^\d+\.', line.strip()):
                # Добавляем строки, которые не являются новыми результатами поиска
                if any(keyword in line.lower() for keyword in ['важно', 'примечание', 'обратите внимание', 'документы', 'стоимость', 'время']):
                    result_lines.append(line)
            
            # Если это не результат поиска, добавляем как есть
            elif not re.match(r'^\d+\.', line.strip()):
                result_lines.append(line)
        
        # Добавляем примечание в конец
        if result_count >= 5:
            result_lines.append("\n💡 **Показаны первые 5 самых актуальных мест для получения медкнижки.**")
            result_lines.append("\n📞 **Для быстрого подключения к ILPO-TAXI звоните:** <a href='tel:+79968073743'>+7 996 807-37-43</a>")
        
        return '\n'.join(result_lines)

# Создаем глобальный экземпляр
openrouter_ai = OpenRouterAI() 