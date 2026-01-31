"""
Скрипт автоматического создания структуры проекта SubsManager
"""

import os

# Корневая папка проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Структура файлов
FILES = {
    # bot/__init__.py
    "bot/__init__.py": '""""SubsManager Bot"""',
    
    # bot/config.py
    "bot/config.py": '''from dataclasses import dataclass

@dataclass
class Config:
    # ========================================
    # ВСТАВЬТЕ СВОЙ ТОКЕН СЮДА ↓↓↓
    # ========================================
    BOT_TOKEN: str = "ВСТАВЬТЕ_ТОКЕН_СЮДА"
    # ========================================
    
    DATABASE_URL: str = "sqlite+aiosqlite:///subscriptions.db"
    BOT_USERNAME: str = "SubsManagerBot"
    WEBAPP_URL: str = ""
    API_URL: str = ""
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    PREMIUM_MONTHLY_PRICE: int = 99
    PREMIUM_YEARLY_PRICE: int = 799
    LIFETIME_PRICE: int = 1499
    FREE_SUBSCRIPTIONS_LIMIT: int = 5
    FREE_REPORTS_LIMIT: int = 3
    DEBUG: bool = True

config = Config()
''',

    # bot/models.py
    "bot/models.py": '''from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, Enum, JSON
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
    premium_type = Column(Enum(PremiumType), default=PremiumType.FREE)
    premium_expires = Column(DateTime, nullable=True)
    notify_before_days = Column(Integer, default=3)
    notify_time = Column(String(5), default="10:00")
    total_saved = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    billing_cycle = Column(Enum(BillingCycle), default=BillingCycle.MONTHLY)
    start_date = Column(Date, nullable=False)
    next_billing_date = Column(Date, nullable=True)
    trial_end_date = Column(Date, nullable=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    is_trial = Column(Boolean, default=False)
    auto_renew = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="subscriptions")

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    remind_date = Column(Date, nullable=False)
    remind_type = Column(String(50), nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    yookassa_payment_id = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    payment_type = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class DuplicateAlert(Base):
    __tablename__ = "duplicate_alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    main_subscription_id = Column(Integer, nullable=False)
    duplicate_subscription_id = Column(Integer, nullable=False)
    overlap_type = Column(String(100), nullable=False)
    potential_saving = Column(Float, nullable=True)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    # bot/database.py
    "bot/database.py": '''from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
''',

    # bot/main.py
    "bot/main.py": '''import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from .config import config
from .database import init_db
from .handlers import setup_routers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "ВСТАВЬТЕ_ТОКЕН_СЮДА":
        logger.error("❌ BOT_TOKEN не указан! Откройте bot/config.py и вставьте токен от @BotFather")
        sys.exit(1)
    
    logger.info("📦 Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова")
    
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот @{bot_info.username} запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n👋 Бот остановлен")

if __name__ == "__main__":
    run()
''',

    # bot/handlers/__init__.py
    "bot/handlers/__init__.py": '''from aiogram import Router
from .start import router as start_router
from .subscriptions import router as subscriptions_router

def setup_routers() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(subscriptions_router)
    return router
''',

    # bot/handlers/start.py
    "bot/handlers/start.py": '''from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from ..database import get_or_create_user, get_monthly_spending, get_user_subscriptions
from ..keyboards.inline import get_main_menu_keyboard
from ..keyboards.reply import get_main_reply_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    text = f"""
👋 Привет, {message.from_user.first_name}!

Я помогу тебе управлять подписками и экономить деньги 💰

🔄 <b>Что я умею:</b>
• Отслеживать все твои подписки
• Напоминать о списаниях заранее
• Находить дубликаты и переплаты
• Показывать аналитику расходов

📱 Начни с добавления своих подписок!
"""
    await message.answer(text, reply_markup=get_main_reply_keyboard())
    await message.answer("Выбери действие:", reply_markup=get_main_menu_keyboard())

@router.message(Command("menu"))
@router.message(F.text == "🏠 Меню")
async def cmd_menu(message: Message):
    subscriptions = await get_user_subscriptions(message.from_user.id)
    monthly = await get_monthly_spending(message.from_user.id)
    
    if subscriptions:
        text = f"""
📊 <b>Твоя статистика:</b>
• Активных подписок: {len(subscriptions)}
• Месячные траты: {monthly:,.0f}₽
• В год: {monthly * 12:,.0f}₽
"""
    else:
        text = "У тебя пока нет подписок. Добавь первую! 👇"
    
    await message.answer(text, reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    subscriptions = await get_user_subscriptions(callback.from_user.id)
    monthly = await get_monthly_spending(callback.from_user.id)
    
    if subscriptions:
        text = f"""
📊 <b>Твоя статистика:</b>
• Активных подписок: {len(subscriptions)}
• Месячные траты: {monthly:,.0f}₽
"""
    else:
        text = "У тебя пока нет подписок. Добавь первую! 👇"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = """
📖 <b>Справка</b>

/start — Начать работу
/menu — Главное меню
/help — Справка
"""
    await message.answer(text)
''',

    # bot/handlers/subscriptions.py
    "bot/handlers/subscriptions.py": '''from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date

from ..database import get_user_subscriptions, add_subscription, get_subscription, delete_subscription, get_monthly_spending
from ..models import BillingCycle, SubscriptionStatus
from ..keyboards.inline import get_main_menu_keyboard, get_subscriptions_list_keyboard, get_subscription_detail_keyboard, get_categories_keyboard, get_cycle_keyboard
from ..keyboards.reply import get_cancel_keyboard, get_main_reply_keyboard

router = Router()

class AddSubscription(StatesGroup):
    entering_name = State()
    entering_price = State()
    choosing_cycle = State()

@router.message(F.text == "📋 Подписки")
@router.callback_query(F.data == "my_subscriptions")
async def show_subscriptions(update: Message | CallbackQuery):
    user_id = update.from_user.id
    subscriptions = await get_user_subscriptions(user_id)
    
    if not subscriptions:
        text = "📋 <b>Мои подписки</b>\\n\\nУ тебя пока нет подписок. Добавь первую! 👇"
        keyboard = get_main_menu_keyboard()
    else:
        monthly = await get_monthly_spending(user_id)
        text = f"📋 <b>Мои подписки</b>\\n\\n📊 Всего: <b>{len(subscriptions)}</b>\\n💰 В месяц: <b>{monthly:,.0f}₽</b>"
        keyboard = get_subscriptions_list_keyboard(subscriptions)
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=keyboard)
        await update.answer()
    else:
        await update.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("view_sub:"))
async def view_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.split(":")[1])
    sub = await get_subscription(sub_id)
    
    if not sub:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    text = f"""
{sub.icon or "📦"} <b>{sub.name}</b>

💰 Стоимость: {sub.price:,.0f}₽
📅 Следующее списание: {sub.next_billing_date.strftime("%d.%m.%Y") if sub.next_billing_date else "—"}
"""
    await callback.message.edit_text(text, reply_markup=get_subscription_detail_keyboard(sub_id))
    await callback.answer()

@router.message(F.text == "➕ Добавить")
@router.callback_query(F.data == "add_subscription")
async def start_add(update: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = "➕ <b>Добавление подписки</b>\\n\\nВыбери категорию или добавь свою:"
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=get_categories_keyboard())
        await update.answer()
    else:
        await update.answer(text, reply_markup=get_categories_keyboard())

@router.callback_query(F.data == "custom_subscription")
async def custom_sub(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введи название подписки:")
    await state.set_state(AddSubscription.entering_name)
    await callback.answer()

@router.message(AddSubscription.entering_name)
async def enter_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    await state.update_data(name=message.text.strip())
    await message.answer("💰 Введи цену (в рублях):", reply_markup=get_cancel_keyboard())
    await state.set_state(AddSubscription.entering_price)

@router.message(AddSubscription.entering_price)
async def enter_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    try:
        price = float(message.text.replace(",", ".").replace("₽", "").strip())
    except ValueError:
        await message.answer("❌ Введи число")
        return
    
    await state.update_data(price=price)
    await message.answer("📅 Выбери период оплаты:", reply_markup=get_cycle_keyboard())
    await state.set_state(AddSubscription.choosing_cycle)

@router.callback_query(F.data.startswith("cycle:"), AddSubscription.choosing_cycle)
async def choose_cycle(callback: CallbackQuery, state: FSMContext):
    cycle = callback.data.split(":")[1]
    cycle_map = {"weekly": BillingCycle.WEEKLY, "monthly": BillingCycle.MONTHLY, "quarterly": BillingCycle.QUARTERLY, "yearly": BillingCycle.YEARLY}
    
    data = await state.get_data()
    await add_subscription(
        telegram_id=callback.from_user.id,
        name=data["name"],
        price=data["price"],
        billing_cycle=cycle_map.get(cycle, BillingCycle.MONTHLY),
        start_date=date.today(),
        icon="📦"
    )
    
    await state.clear()
    await callback.message.edit_text(f"✅ Подписка <b>{data['name']}</b> добавлена!", reply_markup=get_main_menu_keyboard())
    await callback.answer("Добавлено! ✅")

@router.callback_query(F.data.startswith("delete_sub:"))
async def confirm_delete(callback: CallbackQuery):
    sub_id = int(callback.data.split(":")[1])
    sub = await get_subscription(sub_id)
    
    if not sub:
        await callback.answer("Не найдено", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_del:{sub_id}"), InlineKeyboardButton(text="❌ Нет", callback_data=f"view_sub:{sub_id}")]
    ])
    await callback.message.edit_text(f"🗑️ Удалить <b>{sub.name}</b>?", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del:"))
async def do_delete(callback: CallbackQuery):
    sub_id = int(callback.data.split(":")[1])
    await delete_subscription(sub_id)
    await callback.message.edit_text("🗑️ Удалено", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.message(F.text == "📊 Аналитика")
@router.callback_query(F.data == "analytics")
async def analytics(update: Message | CallbackQuery):
    user_id = update.from_user.id
    subs = await get_user_subscriptions(user_id)
    monthly = await get_monthly_spending(user_id)
    
    text = f"""
📊 <b>Аналитика</b>

💰 В месяц: <b>{monthly:,.0f}₽</b>
📅 В год: <b>{monthly * 12:,.0f}₽</b>
📋 Подписок: <b>{len(subs)}</b>
"""
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await update.answer()
    else:
        await update.answer(text, reply_markup=get_main_menu_keyboard())

@router.message(F.text == "⚙️ Настройки")
@router.callback_query(F.data == "settings")
async def settings(update: Message | CallbackQuery):
    text = "⚙️ <b>Настройки</b>\\n\\nСкоро здесь появятся настройки!"
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await update.answer()
    else:
        await update.answer(text, reply_markup=get_main_menu_keyboard())
''',

    # bot/keyboards/__init__.py
    "bot/keyboards/__init__.py": '"""Keyboards"""',

    # bot/keyboards/inline.py
    "bot/keyboards/inline.py": '''from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_subscription"),
        InlineKeyboardButton(text="📋 Подписки", callback_data="my_subscriptions")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Аналитика", callback_data="analytics"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    return builder.as_markup()

def get_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = [
        ("🎬 Видео", "cat:streaming"),
        ("🎵 Музыка", "cat:music"),
        ("🎮 Игры", "cat:gaming"),
        ("☁️ Облако", "cat:cloud"),
    ]
    for name, data in categories:
        builder.add(InlineKeyboardButton(text=name, callback_data=data))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✏️ Своя подписка", callback_data="custom_subscription"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def get_cycle_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Неделя", callback_data="cycle:weekly"),
        InlineKeyboardButton(text="📆 Месяц", callback_data="cycle:monthly")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Квартал", callback_data="cycle:quarterly"),
        InlineKeyboardButton(text="📅 Год", callback_data="cycle:yearly")
    )
    return builder.as_markup()

def get_subscriptions_list_keyboard(subscriptions: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sub in subscriptions[:8]:
        icon = "✅" if sub.status.value == "active" else "⏸️"
        builder.row(InlineKeyboardButton(text=f"{icon} {sub.name} — {sub.price:.0f}₽", callback_data=f"view_sub:{sub.id}"))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_subscription"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
    )
    return builder.as_markup()

def get_subscription_detail_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_sub:{sub_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="my_subscriptions"))
    return builder.as_markup()

def get_back_keyboard(callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]])
''',

    # bot/keyboards/reply.py
    "bot/keyboards/reply.py": '''from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📋 Подписки"), KeyboardButton(text="➕ Добавить"))
    builder.row(KeyboardButton(text="📊 Аналитика"), KeyboardButton(text="⚙️ Настройки"))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
''',

    # bot/services/__init__.py
    "bot/services/__init__.py": '"""Services"""',

    # bot/data/__init__.py
    "bot/data/__init__.py": '"""Data"""',

    # bot/data/subscriptions_catalog.py
    "bot/data/subscriptions_catalog.py": '''SUBSCRIPTION_CATEGORIES = {
    "streaming": "🎬 Видео",
    "music": "🎵 Музыка",
    "gaming": "🎮 Игры",
    "cloud": "☁️ Облако",
    "other": "📦 Другое"
}

SUBSCRIPTIONS_CATALOG = {
    "yandex_plus": {"name": "Яндекс Плюс", "icon": "🟡", "price": 299},
    "spotify": {"name": "Spotify", "icon": "🟢", "price": 199},
}
''',
}

def create_files():
    print("🚀 Создание структуры проекта SubsManager...")
    print(f"📁 Папка: {BASE_DIR}")
    print()
    
    created = 0
    for filepath, content in FILES.items():
        full_path = os.path.join(BASE_DIR, filepath)
        
        # Создаём директорию
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Записываем файл
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"✅ {filepath}")
        created += 1
    
    print()
    print(f"🎉 Создано {created} файлов!")
    print()
    print("=" * 50)
    print("📝 СЛЕДУЮЩИЕ ШАГИ:")
    print("=" * 50)
    print()
    print("1. Откройте файл bot/config.py")
    print("2. Замените ВСТАВЬТЕ_ТОКЕН_СЮДА на токен от @BotFather")
    print("3. Запустите: python -m bot.main")
    print()

if __name__ == "__main__":
    create_files()