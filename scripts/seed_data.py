"""
Скрипт заполнения тестовыми данными
"""

import asyncio
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.database import async_session, get_or_create_user, add_subscription
from bot.models import BillingCycle

# Тестовый пользователь
TEST_USER_ID = 123456789  # Замените на свой Telegram ID

# Тестовые подписки
TEST_SUBSCRIPTIONS = [
    {
        "name": "Яндекс Плюс",
        "price": 299,
        "billing_cycle": BillingCycle.MONTHLY,
        "category": "streaming",
        "icon": "🟡",
        "service_id": "yandex_plus",
        "included_services": ["yandex_music", "kinopoisk"]
    },
    {
        "name": "Telegram Premium",
        "price": 299,
        "billing_cycle": BillingCycle.MONTHLY,
        "category": "communication",
        "icon": "⭐",
        "service_id": "telegram_premium"
    },
    {
        "name": "Spotify",
        "price": 199,
        "billing_cycle": BillingCycle.MONTHLY,
        "category": "music",
        "icon": "🟢",
        "service_id": "spotify"
    },
    {
        "name": "iCloud 50GB",
        "price": 99,
        "billing_cycle": BillingCycle.MONTHLY,
        "category": "cloud",
        "icon": "☁️",
        "service_id": "icloud"
    },
    {
        "name": "Netflix",
        "price": 999,
        "billing_cycle": BillingCycle.MONTHLY,
        "category": "streaming",
        "icon": "🔴",
        "is_trial": True,
        "trial_end_date": date.today() + timedelta(days=5)
    }
]

async def seed():
    print("🌱 Заполнение тестовыми данными...")
    
    # Создаём пользователя
    user = await get_or_create_user(
        telegram_id=TEST_USER_ID,
        username="test_user",
        first_name="Тестовый"
    )
    print(f"👤 Пользователь: {user.telegram_id}")
    
    # Добавляем подписки
    for sub_data in TEST_SUBSCRIPTIONS:
        try:
            sub = await add_subscription(
                telegram_id=TEST_USER_ID,
                start_date=date.today() - timedelta(days=30),
                **sub_data
            )
            print(f"✅ Добавлена: {sub.name}")
        except Exception as e:
            print(f"⚠️  Ошибка: {e}")
    
    print("✅ Готово!")

if __name__ == "__main__":
    asyncio.run(seed())