"""
Скрипт миграции базы данных
Добавляет новые поля без потери данных
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from bot.database import engine

MIGRATIONS = [
    # Миграция 1: Добавление поля total_saved
    {
        "name": "add_total_saved",
        "check": "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='total_saved'",
        "up": "ALTER TABLE users ADD COLUMN total_saved FLOAT DEFAULT 0.0"
    },
    # Миграция 2: Добавление поля included_services
    {
        "name": "add_included_services",
        "check": "SELECT column_name FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='included_services'",
        "up": "ALTER TABLE subscriptions ADD COLUMN included_services JSON"
    },
    # Добавляйте новые миграции здесь
]

async def run_migrations():
    print("🔄 Запуск миграций...")
    
    async with engine.begin() as conn:
        for migration in MIGRATIONS:
            try:
                # Проверяем, нужна ли миграция
                result = await conn.execute(text(migration["check"]))
                exists = result.fetchone()
                
                if exists:
                    print(f"⏭️  {migration['name']}: уже применена")
                    continue
                
                # Применяем миграцию
                await conn.execute(text(migration["up"]))
                print(f"✅ {migration['name']}: применена")
                
            except Exception as e:
                print(f"⚠️  {migration['name']}: {e}")
    
    print("✅ Миграции завершены!")

if __name__ == "__main__":
    asyncio.run(run_migrations())