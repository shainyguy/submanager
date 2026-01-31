from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from datetime import datetime, date, timedelta
from typing import Optional, List

from .config import config
from .models import Base, User, Subscription, SubscriptionStatus, BillingCycle, PremiumType

engine = create_async_engine(config.DATABASE_URL, echo=config.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

async def get_user(telegram_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def is_premium(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user:
        return False
    if user.premium_type == PremiumType.LIFETIME:
        return True
    if user.premium_type != PremiumType.FREE and user.premium_expires and user.premium_expires > datetime.utcnow():
        return True
    return False

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
        subscription = Subscription(user_id=user.id, name=name, price=price, billing_cycle=billing_cycle, start_date=start_date, next_billing_date=next_billing, **kwargs)
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription

async def get_user_subscriptions(telegram_id: int, status: SubscriptionStatus = None) -> List[Subscription]:
    async with async_session() as session:
        user = await get_user(telegram_id)
        if not user:
            return []
        query = select(Subscription).where(Subscription.user_id == user.id)
        if status:
            query = query.where(Subscription.status == status)
        else:
            query = query.where(Subscription.status != SubscriptionStatus.CANCELLED)
        query = query.order_by(Subscription.next_billing_date)
        result = await session.execute(query)
        return list(result.scalars().all())

async def get_subscription(subscription_id: int) -> Optional[Subscription]:
    async with async_session() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
        return result.scalar_one_or_none()

async def update_subscription(subscription_id: int, **kwargs):
    async with async_session() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
        subscription = result.scalar_one_or_none()
        if subscription:
            for key, value in kwargs.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)
            await session.commit()

async def delete_subscription(subscription_id: int):
    async with async_session() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
        subscription = result.scalar_one_or_none()
        if subscription:
            await session.delete(subscription)
            await session.commit()

async def get_monthly_spending(telegram_id: int) -> float:
    subscriptions = await get_user_subscriptions(telegram_id, status=SubscriptionStatus.ACTIVE)
    total = 0.0
    for sub in subscriptions:
        total += get_monthly_equivalent(sub.price, sub.billing_cycle)
    return round(total, 2)

def calculate_next_billing(start_date: date, billing_cycle: BillingCycle) -> date:
    today = date.today()
    next_date = start_date
    while next_date <= today:
        if billing_cycle == BillingCycle.WEEKLY:
            next_date += timedelta(weeks=1)
        elif billing_cycle == BillingCycle.MONTHLY:
            next_date += timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            next_date += timedelta(days=90)
        elif billing_cycle == BillingCycle.YEARLY:
            next_date += timedelta(days=365)
        else:
            break
    return next_date

def get_monthly_equivalent(price: float, billing_cycle: BillingCycle) -> float:
    if billing_cycle == BillingCycle.WEEKLY:
        return price * 4.33
    elif billing_cycle == BillingCycle.MONTHLY:
        return price
    elif billing_cycle == BillingCycle.QUARTERLY:
        return price / 3
    elif billing_cycle == BillingCycle.YEARLY:
        return price / 12
    return price
