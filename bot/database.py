from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from datetime import datetime, date, timedelta
from typing import Optional, List
import os
import logging

from .models import Base, User, Subscription, SubscriptionStatus, BillingCycle, PremiumType

logger = logging.getLogger(__name__)

# ========================================
# ПОЛУЧАЕМ И ИСПРАВЛЯЕМ URL БАЗЫ ДАННЫХ
# ========================================
def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///subscriptions.db")
    
    # Railway использует postgresql:// или postgres://
    # Нам нужен postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    return url

DATABASE_URL = get_database_url()

# Логируем (без пароля)
if "@" in DATABASE_URL:
    safe_url = DATABASE_URL.split("@")[-1]
    logger.info(f"📦 Database: ...@{safe_url}")
else:
    logger.info(f"📦 Database: {DATABASE_URL}")

# ========================================
# СОЗДАЁМ ENGINE
# ========================================
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ========================================
# ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЯМИ
# ========================================
async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            if username: user.username = username
            if first_name: user.first_name = first_name
            await session.commit()
        return user

async def get_user(telegram_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def is_premium(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user: return False
    if user.premium_type == PremiumType.LIFETIME: return True
    if user.premium_type != PremiumType.FREE and user.premium_expires and user.premium_expires > datetime.utcnow():
        return True
    return False

# ========================================
# ОПЕРАЦИИ С ПОДПИСКАМИ
# ========================================
async def add_subscription(telegram_id: int, name: str, price: float, billing_cycle: BillingCycle, start_date: date, **kwargs) -> Subscription:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        next_billing = calculate_next_billing(start_date, billing_cycle)
        sub = Subscription(
            user_id=user.id, 
            name=name, 
            price=price, 
            billing_cycle=billing_cycle, 
            start_date=start_date, 
            next_billing_date=next_billing, 
            **kwargs
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

async def get_user_subscriptions(telegram_id: int) -> List[Subscription]:
    async with async_session() as session:
        user = await get_user(telegram_id)
        if not user: return []
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status != SubscriptionStatus.CANCELLED)
            .order_by(Subscription.next_billing_date)
        )
        return list(result.scalars().all())

async def get_subscription(subscription_id: int) -> Optional[Subscription]:
    async with async_session() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
        return result.scalar_one_or_none()

async def delete_subscription(subscription_id: int):
    async with async_session() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
        sub = result.scalar_one_or_none()
        if sub:
            await session.delete(sub)
            await session.commit()

async def get_monthly_spending(telegram_id: int) -> float:
    subs = await get_user_subscriptions(telegram_id)
    total = 0.0
    for s in subs:
        if s.status == SubscriptionStatus.ACTIVE:
            total += get_monthly_equivalent(s.price, s.billing_cycle)
    return round(total, 2)

async def get_subscriptions_count(telegram_id: int) -> int:
    subs = await get_user_subscriptions(telegram_id)
    return len(subs)

# ========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ========================================
def calculate_next_billing(start_date: date, cycle: BillingCycle) -> date:
    today = date.today()
    next_date = start_date
    while next_date <= today:
        if cycle == BillingCycle.WEEKLY: 
            next_date += timedelta(weeks=1)
        elif cycle == BillingCycle.MONTHLY: 
            next_date += timedelta(days=30)
        elif cycle == BillingCycle.QUARTERLY: 
            next_date += timedelta(days=90)
        elif cycle == BillingCycle.YEARLY: 
            next_date += timedelta(days=365)
        else: 
            break
    return next_date

def get_monthly_equivalent(price: float, cycle: BillingCycle) -> float:
    if cycle == BillingCycle.WEEKLY: return price * 4.33
    elif cycle == BillingCycle.MONTHLY: return price
    elif cycle == BillingCycle.QUARTERLY: return price / 3
    elif cycle == BillingCycle.YEARLY: return price / 12
    return price

# ========================================
# ДОБАВЬТЕ ЭТИ ФУНКЦИИ В database.py
# ========================================

async def add_subscription(
    telegram_id: int, 
    name: str, 
    price: float, 
    billing_cycle: BillingCycle, 
    start_date: date,
    icon: str = None,
    category: str = None,
    color: str = None,
    currency: str = "RUB",
    notify_days: int = 3,
    **kwargs
) -> Subscription:
    """Добавить подписку с поддержкой всех полей"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        next_billing = calculate_next_billing(start_date, billing_cycle)
        
        sub = Subscription(
            user_id=user.id, 
            name=name, 
            price=price, 
            billing_cycle=billing_cycle, 
            start_date=start_date, 
            next_billing_date=next_billing,
            icon=icon,
            category=category,
            color=color,
            currency=currency,
            **kwargs
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


async def update_subscription(
    subscription_id: int,
    name: str = None,
    price: float = None,
    next_payment: str = None,
    icon: str = None,
    category: str = None,
    color: str = None,
    billing_cycle: BillingCycle = None,
    status: SubscriptionStatus = None,
    **kwargs
) -> Optional[Subscription]:
    """Обновить подписку"""
    async with async_session() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        sub = result.scalar_one_or_none()
        
        if not sub:
            return None
        
        # Обновляем только переданные поля
        if name is not None:
            sub.name = name
        if price is not None:
            sub.price = price
        if icon is not None:
            sub.icon = icon
        if category is not None:
            sub.category = category
        if color is not None:
            sub.color = color
        if billing_cycle is not None:
            sub.billing_cycle = billing_cycle
        if status is not None:
            sub.status = status
        if next_payment is not None:
            try:
                if isinstance(next_payment, str):
                    sub.next_billing_date = datetime.fromisoformat(
                        next_payment.replace('Z', '+00:00')
                    ).date()
                elif isinstance(next_payment, date):
                    sub.next_billing_date = next_payment
            except:
                pass
        
        await session.commit()
        await session.refresh(sub)
        return sub


async def get_subscription_by_id(subscription_id: int) -> Optional[Subscription]:
    """Получить подписку по ID"""
    async with async_session() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()


async def create_user(
    telegram_id: int, 
    username: str = None, 
    first_name: str = None
) -> User:
    """Создать нового пользователя"""
    async with async_session() as session:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_all_subscriptions(telegram_id: int) -> List[Subscription]:
    """Получить ВСЕ подписки (включая отменённые) для аналитики"""
    async with async_session() as session:
        user = await get_user(telegram_id)
        if not user:
            return []
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.next_billing_date)
        )
        return list(result.scalars().all())


async def get_upcoming_payments(telegram_id: int, days: int = 7) -> List[Subscription]:
    """Получить подписки со скорым списанием"""
    async with async_session() as session:
        user = await get_user(telegram_id)
        if not user:
            return []
        
        today = date.today()
        end_date = today + timedelta(days=days)
        
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
            .where(Subscription.next_billing_date >= today)
            .where(Subscription.next_billing_date <= end_date)
            .order_by(Subscription.next_billing_date)
        )
        return list(result.scalars().all())


async def set_premium(
    telegram_id: int, 
    premium_type: PremiumType, 
    expires: datetime = None
) -> User:
    """Установить премиум статус пользователю"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
        
        user.premium_type = premium_type
        user.premium_expires = expires
        
        await session.commit()
        await session.refresh(user)
        return user

