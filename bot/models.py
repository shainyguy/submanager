from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Date, ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
import enum

class Base(AsyncAttrs, DeclarativeBase):
    pass

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    TRIAL = "trial"

class BillingCycle(enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class PremiumType(enum.Enum):
    FREE = "free"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    language = Column(String(10), default="ru")
    timezone = Column(String(50), default="Europe/Moscow")
    
    # Премиум статус
    premium_type = Column(Enum(PremiumType), default=PremiumType.FREE)
    premium_expires = Column(DateTime, nullable=True)
    
    # Настройки уведомлений
    notify_before_days = Column(Integer, default=3)
    notify_time = Column(String(5), default="10:00")
    notify_monthly_report = Column(Boolean, default=True)
    
    # Статистика
    total_saved = Column(Float, default=0.0)  # Сколько сэкономил благодаря боту
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Основная информация
    service_id = Column(String(100), nullable=True)  # ID из каталога
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    icon = Column(String(50), nullable=True)  # Эмодзи
    color = Column(String(7), nullable=True)  # HEX цвет
    
    # Финансы
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    billing_cycle = Column(Enum(BillingCycle), default=BillingCycle.MONTHLY)
    
    # Даты
    start_date = Column(Date, nullable=False)
    next_billing_date = Column(Date, nullable=True)
    trial_end_date = Column(Date, nullable=True)
    
    # Статус
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    is_trial = Column(Boolean, default=False)
    auto_renew = Column(Boolean, default=True)
    
    # Дополнительно
    notes = Column(Text, nullable=True)
    payment_method = Column(String(100), nullable=True)  # Карта, СБП и т.д.
    
    # Для детектора дубликатов
    included_services = Column(JSON, nullable=True)  # Список включённых сервисов
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="subscriptions")
    reminders = relationship("Reminder", back_populates="subscription", cascade="all, delete-orphan")

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    
    remind_date = Column(Date, nullable=False)
    remind_type = Column(String(50), nullable=False)  # billing, trial_end, cancel
    message = Column(Text, nullable=True)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subscription = relationship("Subscription", back_populates="reminders")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    yookassa_payment_id = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    
    payment_type = Column(String(50), nullable=False)  # premium_monthly, premium_yearly, lifetime
    status = Column(String(50), default="pending")  # pending, succeeded, cancelled
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="payments")

class DuplicateAlert(Base):
    __tablename__ = "duplicate_alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    main_subscription_id = Column(Integer, nullable=False)
    duplicate_subscription_id = Column(Integer, nullable=False)
    
    overlap_type = Column(String(100), nullable=False)  # included, similar, redundant
    potential_saving = Column(Float, nullable=True)
    recommendation = Column(Text, nullable=True)
    
    is_dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)