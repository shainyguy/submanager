
---

### 📄 scripts/init_db.py

```python
"""
Скрипт инициализации базы данных
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.database import init_db, engine
from bot.models import Base

async def main():
    print("🔧 Инициализация базы данных...")
    
    try:
        await init_db()
        print("✅ База данных успешно инициализирована!")
        
        # Выводим список таблиц
        async with engine.begin() as conn:
            from sqlalchemy import inspect
            
            def get_tables(connection):
                inspector = inspect(connection)
                return inspector.get_table_names()
            
            tables = await conn.run_sync(get_tables)
            print(f"📋 Созданные таблицы: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
