import os
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    PORT: str = os.getenv("PORT", "8000")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "SubsManagerBot")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    PREMIUM_MONTHLY_PRICE: int = 99
    PREMIUM_YEARLY_PRICE: int = 799
    LIFETIME_PRICE: int = 1499
    FREE_SUBSCRIPTIONS_LIMIT: int = 5
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

config = Config()
