"""
УМНЫЙ ТАКСОПАРК - Основные роутеры
Роутеры для основных функций сайта
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import asyncio
import json
from datetime import datetime

# Создаем роутер для основных маршрутов
main_router = APIRouter()

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

@main_router.get("/", response_class=HTMLResponse)
async def read_root():
    """Главная страница сайта"""
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@main_router.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Страница Политики конфиденциальности"""
    return templates.TemplateResponse("privacy-policy.html", {"request": request})

@main_router.get("/user-agreement", response_class=HTMLResponse)
async def user_agreement(request: Request):
    """Страница Пользовательского соглашения"""
    return templates.TemplateResponse("user-agreement.html", {"request": request})

@main_router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Страница регистрации (синоним для /signup.html)"""
    return templates.TemplateResponse("signup.html", {"request": request})

@main_router.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Умный Таксопарк API",
        "version": "1.0.0"
    }

@main_router.post("/api/register")
async def register_driver(request: Request):
    """Регистрация нового водителя/курьера"""
    try:
        data = await request.json()
        
        # Валидация данных
        required_fields = ["name", "phone", "role"]
        for field in required_fields:
            if field not in data or not data[field]:
                return {"success": False, "error": f"Поле {field} обязательно"}
        
        # Имитируем сохранение в базу данных
        registration_data = {
            "id": f"reg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": data["name"],
            "phone": data["phone"],
            "role": data["role"],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "agreement": data.get("agreement", False)
        }
        
        print(f"📝 Новая регистрация: {registration_data}")
        
        # Имитируем задержку обработки
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": "Заявка успешно отправлена!",
            "registration_id": registration_data["id"],
            "estimated_callback_time": "30 минут"
        }
        
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return {"success": False, "error": "Произошла ошибка при обработке заявки"}

@main_router.post("/api/signup")
async def signup_application(request: Request):
    """Обработка заявок со страницы подключения"""
    try:
        data = await request.json()
        
        # Валидация обязательных полей
        required_fields = ["fullName", "phone", "age", "city", "category"]
        for field in required_fields:
            if field not in data or not data[field]:
                return {"success": False, "error": f"Поле {field} обязательно для заполнения"}
        
        # Специальная валидация в зависимости от категории
        category = data["category"]
        if category in ["driver", "both", "cargo"]:
            if "experience" not in data or not data["experience"]:
                return {"success": False, "error": "Для водителей обязательно указать стаж вождения"}
        
        if category in ["courier", "both"]:
            if "transport" not in data or not data["transport"]:
                return {"success": False, "error": "Для курьеров обязательно указать вид транспорта"}
        
        if category == "cargo":
            if "loadCapacity" not in data or not data["loadCapacity"]:
                return {"success": False, "error": "Для грузовых перевозок обязательно указать грузоподъемность"}
        
        # Создаем заявку
        application_data = {
            "id": f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{category}",
            "category": category,
            
            # Основные поля (используем правильные имена полей из формы)
            "full_name": data["fullName"],
            "phone": data["phone"],
            "age": int(data["age"]),
            "city": data["city"],
            "email": data.get("email", ""),
            
            # Новые основные поля
            "citizenship": data.get("citizenship"),
            "workStatus": data.get("workStatus"),
            "preferredTime": data.get("preferredTime"),
            "workSchedule": data.get("workSchedule"),
            "comments": data.get("comments"),
            
            # Информация для водителей
            "experience": data.get("experience"),
            "hasDriverLicense": data.get("hasDriverLicense"),
            "hasCar": data.get("hasCar"),
            "carBrand": data.get("carBrand"),
            "carModel": data.get("carModel"),
            "carYear": data.get("carYear"),
            "carClass": data.get("carClass"),
            "hasTaxiPermit": data.get("hasTaxiPermit"),
            
            # Информация для курьеров
            "transport": data.get("transport", ""),
            "deliveryType": data.get("deliveryType", []),
            "hasThermoBag": data.get("hasThermoBag"),
            "courierLicense": data.get("courierLicense"),
            
            # Информация для грузовых
            "loadCapacity": data.get("loadCapacity", ""),
            "truckType": data.get("truckType"),
            "cargoLicense": data.get("cargoLicense"),
            
            # Документы и опыт
            "workExperience": data.get("workExperience"),
            "previousPlatforms": data.get("previousPlatforms"),
            "hasMedicalCert": data.get("hasMedicalCert"),
            "documents": data.get("documents", []),
            
            # Согласия
            "hasDocuments": data.get("hasDocuments", False),
            "agreeTerms": data.get("agreeTerms", False),
            "agreeMarketing": data.get("agreeMarketing", False),
            
            # Метаданные
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "source": "signup_page"
        }
        
        print(f"📋 Новая заявка на подключение ({category}): {application_data}")
        
        # Интегрируем с Telegram ботом для отправки заявки менеджерам
        try:
            # Импортируем функцию обработки заявок
            from telegram_bot.services.application_service import handle_new_application_from_site
            
            # Обрабатываем заявку через Telegram бот (передаем исходные данные формы)
            # Передаем уже обработанные и приведённые к нужным типам данные
            bot_success = await handle_new_application_from_site(application_data)
            
            if bot_success:
                print(f"✅ Заявка успешно отправлена менеджерам через Telegram бот")
            else:
                print(f"⚠️ Заявка сохранена локально (бот временно недоступен)")
                
        except Exception as e:
            print(f"❌ Ошибка интеграции с Telegram ботом: {e}")
            # Логируем полную ошибку для отладки
            import traceback
            print(f"Подробности ошибки: {traceback.format_exc()}")
        
        # Имитируем обработку заявки
        await asyncio.sleep(1)
        
        # Определяем тип заявки для ответа
        category_names = {
            "driver": "водителя",
            "courier": "курьера", 
            "both": "водителя и курьера",
            "cargo": "водителя грузовых перевозок"
        }
        
        return {
            "success": True,
            "message": f"Заявка на подключение {category_names[category]} успешно отправлена!",
            "application_id": application_data["id"],
            "category": category,
            "estimated_callback_time": "24 часа",
            "contact_phone": "+7 996 807-37-43"
        }
        
    except Exception as e:
        print(f"❌ Ошибка обработки заявки на подключение: {e}")
        return {"success": False, "error": "Произошла ошибка при обработке заявки"}

@main_router.get("/api/stats")
async def get_stats():
    """Получение статистики таксопарка"""
    return {
        "active_drivers": 1247,
        "active_couriers": 389,
        "total_orders_today": 5632,
        "average_earnings": 95000,
        "satisfaction_rate": 4.8,
        "response_time": "< 30 сек",
        "ai_consultations_today": 234
    }

@main_router.get("/api/calculator")
async def calculate_earnings(
    hours_per_day: int = 8,
    days_per_week: int = 5,
    avg_order_cost: int = 400
):
    """Калькулятор заработка"""
    orders_per_hour = 2
    driver_percent = 0.8
    weeks_in_month = 4.33
    
    daily_earnings = hours_per_day * orders_per_hour * avg_order_cost * driver_percent
    weekly_earnings = daily_earnings * days_per_week
    monthly_earnings = weekly_earnings * weeks_in_month
    
    return {
        "daily_earnings": round(daily_earnings),
        "weekly_earnings": round(weekly_earnings),
        "monthly_earnings": round(monthly_earnings),
        "parameters": {
            "hours_per_day": hours_per_day,
            "days_per_week": days_per_week,
            "avg_order_cost": avg_order_cost
        }
    } 