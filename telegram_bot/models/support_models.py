"""
Модели базы данных для системы поддержки ILPO-TAXI
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from telegram_bot.models.database import Base
import uuid

class ApplicationStatus(str, Enum):
    """Статусы заявок"""
    NEW = "new"                    # Новая заявка
    ASSIGNED = "assigned"          # Назначена менеджеру
    IN_PROGRESS = "in_progress"    # В работе
    WAITING_CLIENT = "waiting_client"  # Ожидание клиента
    COMPLETED = "completed"        # Завершена
    CANCELLED = "cancelled"        # Отменена

class ManagerStatus(str, Enum):
    """Статусы менеджеров"""
    ONLINE = "online"      # Онлайн
    BUSY = "busy"          # Занят
    OFFLINE = "offline"    # Офлайн

class ChatType(str, Enum):
    """Типы чатов"""
    WEB_CHAT = "web_chat"          # Веб-чат с сайта
    TELEGRAM_DIRECT = "telegram_direct"  # Прямое обращение в Telegram
    TRANSFER_FROM_AI = "transfer_from_ai"  # Перевод от ИИ-консультанта

class Application(Base):
    """Модель заявки с сайта"""
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    full_name = Column(String(255), nullable=False, comment="ФИО клиента")
    phone = Column(String(20), nullable=False, comment="Телефон клиента")
    age = Column(Integer, nullable=True, comment="Возраст")
    city = Column(String(100), nullable=False, comment="Город")
    category = Column(String(50), nullable=False, comment="Категория: driver, courier, both, cargo")
    email = Column(String(255), nullable=True, comment="Email клиента")
    
    # Новые основные поля
    citizenship = Column(String(50), nullable=True, comment="Гражданство: rf, eaeu, other")
    work_status = Column(String(100), nullable=True, comment="Предпочитаемый статус работы")
    preferred_time = Column(String(50), nullable=True, comment="Удобное время для звонка")
    work_schedule = Column(String(100), nullable=True, comment="Предпочитаемый график работы")
    comments = Column(Text, nullable=True, comment="Дополнительные комментарии")
    
    # Информация для водителей (расширенная)
    experience = Column(String(50), nullable=True, comment="Стаж вождения")
    has_driver_license = Column(String(50), nullable=True, comment="Наличие водительских прав")
    has_car = Column(String(50), nullable=True, comment="Наличие автомобиля")
    car_brand = Column(String(100), nullable=True, comment="Марка автомобиля")
    car_model = Column(String(100), nullable=True, comment="Модель автомобиля")
    car_year = Column(Integer, nullable=True, comment="Год выпуска автомобиля")
    car_class = Column(String(50), nullable=True, comment="Желаемый класс автомобиля")
    has_taxi_permit = Column(String(50), nullable=True, comment="Наличие разрешения на такси")
    
    # Информация для курьеров (расширенная)
    transport = Column(String(50), nullable=True, comment="Вид транспорта для курьеров")
    delivery_types = Column(JSON, nullable=True, comment="Категории доставки (массив)")
    has_thermo_bag = Column(String(50), nullable=True, comment="Наличие термосумки")
    courier_license = Column(String(50), nullable=True, comment="Права для автокурьеров")
    
    # Информация для грузовых перевозок (расширенная)
    load_capacity = Column(String(50), nullable=True, comment="Грузоподъемность")
    truck_type = Column(String(50), nullable=True, comment="Тип кузова")
    cargo_license = Column(String(50), nullable=True, comment="Права на грузовой транспорт")
    
    # Документы и опыт (новые поля)
    work_experience = Column(String(100), nullable=True, comment="Опыт работы в такси/доставке")
    previous_platforms = Column(String(255), nullable=True, comment="Предыдущие платформы работы")
    has_medical_cert = Column(String(50), nullable=True, comment="Наличие медицинской справки")
    available_documents = Column(JSON, nullable=True, comment="Имеющиеся документы (массив)")
    
    # Согласия (новые поля)
    has_documents_confirmed = Column(Boolean, default=False, comment="Подтвердил наличие документов")
    agree_terms = Column(Boolean, default=False, comment="Согласие с условиями работы")
    agree_marketing = Column(Boolean, default=False, comment="Согласие на рассылку")
    
    # Дополнительная информация (сохраняем как есть для совместимости)
    additional_info = Column(Text, nullable=True, comment="Дополнительная информация")
    
    # Статус и обработка
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.NEW, comment="Статус заявки")
    assigned_manager_id = Column(Integer, ForeignKey("managers.id"), nullable=True, comment="Назначенный менеджер")
    notes = Column(Text, nullable=True, comment="Заметки менеджера")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Время создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Время обновления")
    processed_at = Column(DateTime(timezone=True), nullable=True, comment="Время обработки")
    
    # Связи
    assigned_manager = relationship("Manager", back_populates="applications")
    support_chats = relationship("SupportChat", back_populates="application")

class Manager(Base):
    """Модель менеджера поддержки"""
    __tablename__ = "managers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Telegram информация
    telegram_id = Column(BigInteger, unique=True, nullable=False, comment="Telegram ID менеджера")
    username = Column(String(100), nullable=True, comment="Telegram username")
    first_name = Column(String(100), nullable=False, comment="Имя")
    last_name = Column(String(100), nullable=True, comment="Фамилия")
    
    # Статус и настройки
    status = Column(SQLEnum(ManagerStatus), default=ManagerStatus.OFFLINE, comment="Статус менеджера")
    is_active = Column(Boolean, default=True, comment="Активен ли менеджер")
    is_admin = Column(Boolean, default=False, comment="Является ли администратором")
    max_active_chats = Column(Integer, default=5, comment="Максимум активных чатов")
    
    # Статистика
    total_applications = Column(Integer, default=0, comment="Всего обработано заявок")
    avg_response_time = Column(Integer, default=0, comment="Среднее время ответа в секундах")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Время регистрации")
    last_seen = Column(DateTime(timezone=True), nullable=True, comment="Последняя активность")
    
    # Связи
    applications = relationship("Application", back_populates="assigned_manager")
    support_chats = relationship("SupportChat", back_populates="manager")

class SupportChat(Base):
    """Модель чата поддержки"""
    __tablename__ = "support_chats"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    chat_id = Column(String(100), unique=True, nullable=False, comment="Уникальный ID чата")
    chat_type = Column(SQLEnum(ChatType), nullable=False, comment="Тип чата")
    
    # Участники
    client_telegram_id = Column(BigInteger, nullable=True, comment="Telegram ID клиента")
    client_name = Column(String(200), nullable=True, comment="Имя клиента")
    client_phone = Column(String(20), nullable=True, comment="Телефон клиента")
    
    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=True, comment="Назначенный менеджер")
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, comment="Связанная заявка")
    
    # Статус чата
    is_active = Column(Boolean, default=True, comment="Активен ли чат")
    is_ai_handed_over = Column(Boolean, default=False, comment="Передан ли от ИИ")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Время создания")
    closed_at = Column(DateTime(timezone=True), nullable=True, comment="Время закрытия")
    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="Время последнего сообщения")
    
    # Дополнительная информация
    tags = Column(JSON, nullable=True, comment="Теги чата")
    chat_metadata = Column(JSON, nullable=True, comment="Дополнительные метаданные")
    
    # Связи
    manager = relationship("Manager", back_populates="support_chats")
    application = relationship("Application", back_populates="support_chats")
    messages = relationship("ChatMessage", back_populates="chat")

class ChatMessage(Base):
    """Модель сообщения в чате поддержки"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с чатом
    chat_id = Column(Integer, ForeignKey("support_chats.id"), nullable=False, comment="ID чата")
    
    # Отправитель
    sender_type = Column(String(20), nullable=False, comment="client, manager, system")
    sender_telegram_id = Column(BigInteger, nullable=True, comment="Telegram ID отправителя")
    sender_name = Column(String(200), nullable=True, comment="Имя отправителя")
    
    # Содержимое сообщения
    message_text = Column(Text, nullable=False, comment="Текст сообщения")
    message_type = Column(String(20), default="text", comment="Тип: text, photo, document, etc.")
    file_url = Column(String(500), nullable=True, comment="URL файла если есть")
    
    # Метаданные
    telegram_message_id = Column(String(50), nullable=True, comment="ID сообщения в Telegram")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Время отправки")
    is_read = Column(Boolean, default=False, comment="Прочитано ли сообщение")
    
    # Связи
    chat = relationship("SupportChat", back_populates="messages")

class ManagerWorkSession(Base):
    """Модель рабочей сессии менеджера"""
    __tablename__ = "manager_work_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=False, comment="ID менеджера")
    
    # Время сессии
    started_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Начало сессии")
    ended_at = Column(DateTime(timezone=True), nullable=True, comment="Конец сессии")
    
    # Статистика сессии
    applications_processed = Column(Integer, default=0, comment="Обработано заявок")
    chats_handled = Column(Integer, default=0, comment="Обработано чатов")
    avg_response_time = Column(Integer, default=0, comment="Среднее время ответа")
    
    # Связи
    manager = relationship("Manager")

# Индексы для оптимизации запросов
from sqlalchemy import Index

# Индексы для быстрого поиска заявок
Index('idx_applications_status', Application.status)
Index('idx_applications_created', Application.created_at)
Index('idx_applications_phone', Application.phone)

# Индексы для менеджеров
Index('idx_managers_telegram_id', Manager.telegram_id)
Index('idx_managers_status', Manager.status)

# Индексы для чатов
Index('idx_support_chats_active', SupportChat.is_active)
Index('idx_support_chats_manager', SupportChat.manager_id)
Index('idx_support_chats_created', SupportChat.created_at)

# Индексы для сообщений
Index('idx_chat_messages_chat', ChatMessage.chat_id)
Index('idx_chat_messages_created', ChatMessage.created_at) 