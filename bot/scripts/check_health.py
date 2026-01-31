"""
Скрипт проверки здоровья системы
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import config

async def check_health():
    print("🏥 Проверка системы...\n")
    
    errors = []
    warnings = []
    
    # 1. Проверка BOT_TOKEN
    print("1️⃣ BOT_TOKEN:", end=" ")
    if config.BOT_TOKEN:
        print("✅ Настроен")
    else:
        print("❌ Не настроен")
        errors.append("BOT_TOKEN не указан")
    
    # 2. Проверка DATABASE_URL
    print("2️⃣ DATABASE_URL:", end=" ")
    if config.DATABASE_URL:
        if "postgresql" in config.DATABASE_URL:
            print("✅ PostgreSQL")
        elif "sqlite" in config.DATABASE_URL:
            print("⚠️ SQLite (только для разработки)")
            warnings.append("SQLite не рекомендуется для продакшена")
        else:
            print("✅ Настроен")
    else:
        print("❌ Не настроен")
        errors.append("DATABASE_URL не указан")
    
    # 3. Проверка подключения к БД
    print("3️⃣ Подключение к БД:", end=" ")
    try:
        from bot.database import engine
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        print("✅ Успешно")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        errors.append(f"Не удалось подключиться к БД: {e}")
    
    # 4. Проверка ЮKassa
    print("4️⃣ ЮKassa:", end=" ")
    if config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY:
        print("✅ Настроена")
    else:
        print("⚠️ Не настроена (платежи недоступны)")
        warnings.append("ЮKassa не настроена — премиум не будет работать")
    
    # 5. Проверка WEBAPP_URL
    print("5️⃣ WEBAPP_URL:", end=" ")
    if config.WEBAPP_URL:
        print(f"✅ {config.WEBAPP_URL}")
    else:
        print("⚠️ Не настроен (Mini App недоступен)")
        warnings.append("WEBAPP_URL не указан — Mini App не будет работать")
    
    # 6. Проверка импортов
    print("6️⃣ Импорты:", end=" ")
    try:
        from bot.handlers import setup_routers
        from bot.services.duplicate_detector import detect_duplicates
        from bot.services.smart_analytics import generate_full_report
        print("✅ Все модули загружены")
    except ImportError as e:
        print(f"❌ Ошибка: {e}")
        errors.append(f"Ошибка импорта: {e}")
    
    # Итоги
    print("\n" + "=" * 40)
    
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
        for err in errors:
            print(f"   • {err}")
    
    if warnings:
        print(f"⚠️ Предупреждений: {len(warnings)}")
        for warn in warnings:
            print(f"   • {warn}")
    
    if not errors and not warnings:
        print("✅ Всё готово к запуску!")
    elif not errors:
        print("\n✅ Критических ошибок нет, можно запускать")
    else:
        print("\n❌ Исправьте ошибки перед запуском")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_health())