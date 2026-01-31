import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "SubsManagerBot")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///subscriptions.db")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
    API_URL: str = os.getenv("API_URL", "")
    
    # ЮKassa
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    
    # Премиум цены (мягкие, не давящие)
    PREMIUM_MONTHLY_PRICE: int = int(os.getenv("PREMIUM_MONTHLY_PRICE", "99"))
    PREMIUM_YEARLY_PRICE: int = int(os.getenv("PREMIUM_YEARLY_PRICE", "799"))
    LIFETIME_PRICE: int = int(os.getenv("LIFETIME_PRICE", "1499"))
    
    # Лимиты бесплатной версии (достаточно щедрые)
    FREE_SUBSCRIPTIONS_LIMIT: int = int(os.getenv("FREE_SUBSCRIPTIONS_LIMIT", "5"))
    FREE_REPORTS_LIMIT: int = int(os.getenv("FREE_REPORTS_LIMIT", "3"))
    
    # Режим разработки
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

config = Config()