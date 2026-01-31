"""
🌐 API сервер для webhook'ов и Mini App
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import logging
import json

from bot.services.payment import process_webhook_notification
from bot.database import (
    get_user_subscriptions, get_monthly_spending, 
    get_user, add_subscription, update_subscription, delete_subscription
)
from bot.services.smart_analytics import generate_full_report
from bot.services.duplicate_detector import detect_duplicates
from bot.models import BillingCycle
from datetime import date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SubsManager API", version="1.0.0")

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ МОДЕЛИ ============

class SubscriptionCreate(BaseModel):
    name: str
    price: float
    billing_cycle: str = "monthly"
    category: Optional[str] = None
    start_date: Optional[str] = None
    is_trial: bool = False
    trial_end_date: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    billing_cycle: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TelegramAuthData(BaseModel):
    """Данные авторизации из Telegram Mini App"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    auth_date: int
    hash: str


# ============ WEBHOOK ЭНДПОИНТЫ ============

@app.post("/webhook/yookassa")
async def yookassa_webhook(request: Request):
    """
    Webhook для уведомлений от ЮKassa
    """
    try:
        body = await request.json()
        logger.info(f"Получен webhook от ЮKassa: {body.get('event')}")
        
        success = await process_webhook_notification(body)
        
        if success:
            return JSONResponse({"status": "ok"})
        else:
            raise HTTPException(status_code=400, detail="Failed to process webhook")
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ API ДЛЯ MINI APP ============

@app.get("/api/health")
async def health_check():
    """Проверка работоспособности"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/user/{telegram_id}")
async def get_user_info(telegram_id: int):
    """Получить информацию о пользователе"""
    
    user = await get_user(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.telegram_id,
        "first_name": user.first_name,
        "username": user.username,
        "premium_type": user.premium_type.value,
        "premium_expires": user.premium_expires.isoformat() if user.premium_expires else None,
        "total_saved": user.total_saved,
        "created_at": user.created_at.isoformat()
    }


@app.get("/api/user/{telegram_id}/subscriptions")
async def get_subscriptions(telegram_id: int):
    """Получить подписки пользователя"""
    
    subscriptions = await get_user_subscriptions(telegram_id)
    
    return {
        "subscriptions": [
            {
                "id": sub.id,
                "name": sub.name,
                "price": sub.price,
                "currency": sub.currency,
                "billing_cycle": sub.billing_cycle.value,
                "category": sub.category,
                "icon": sub.icon,
                "color": sub.color,
                "status": sub.status.value,
                "is_trial": sub.is_trial,
                "trial_end_date": sub.trial_end_date.isoformat() if sub.trial_end_date else None,
                "next_billing_date": sub.next_billing_date.isoformat() if sub.next_billing_date else None,
                "notes": sub.notes
            }
            for sub in subscriptions
        ],
        "count": len(subscriptions)
    }


@app.post("/api/user/{telegram_id}/subscriptions")
async def create_subscription(telegram_id: int, data: SubscriptionCreate):
    """Создать подписку"""
    
    cycle_map = {
        "weekly": BillingCycle.WEEKLY,
        "monthly": BillingCycle.MONTHLY,
        "quarterly": BillingCycle.QUARTERLY,
        "yearly": BillingCycle.YEARLY,
    }
    
    start = date.fromisoformat(data.start_date) if data.start_date else date.today()
    trial_end = date.fromisoformat(data.trial_end_date) if data.trial_end_date else None
    
    subscription = await add_subscription(
        telegram_id=telegram_id,
        name=data.name,
        price=data.price,
        billing_cycle=cycle_map.get(data.billing_cycle, BillingCycle.MONTHLY),
        start_date=start,
        category=data.category,
        is_trial=data.is_trial,
        trial_end_date=trial_end
    )
    
    return {
        "id": subscription.id,
        "name": subscription.name,
        "message": "Subscription created"
    }


@app.patch("/api/subscriptions/{subscription_id}")
async def update_subscription_api(subscription_id: int, data: SubscriptionUpdate):
    """Обновить подписку"""
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if "billing_cycle" in update_data:
        cycle_map = {
            "weekly": BillingCycle.WEEKLY,
            "monthly": BillingCycle.MONTHLY,
            "quarterly": BillingCycle.QUARTERLY,
            "yearly": BillingCycle.YEARLY,
        }
        update_data["billing_cycle"] = cycle_map.get(update_data["billing_cycle"])
    
    await update_subscription(subscription_id, **update_data)
    
    return {"message": "Subscription updated"}


@app.delete("/api/subscriptions/{subscription_id}")
async def delete_subscription_api(subscription_id: int):
    """Удалить подписку"""
    
    await delete_subscription(subscription_id)
    
    return {"message": "Subscription deleted"}


@app.get("/api/user/{telegram_id}/analytics")
async def get_analytics(telegram_id: int):
    """Получить аналитику"""
    
    report = await generate_full_report(telegram_id)
    
    return {
        "total_monthly": report.total_monthly,
        "total_yearly": report.total_yearly,
        "subscriptions_count": report.subscriptions_count,
        "active_count": report.active_count,
        "paused_count": report.paused_count,
        "trials_count": report.trials_count,
        "avg_subscription_price": report.avg_subscription_price,
        "by_category": [
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name,
                "emoji": cat.emoji,
                "amount": cat.amount,
                "percent": cat.percent,
                "count": cat.subscriptions_count
            }
            for cat in report.by_category
        ],
        "tips": [
            {
                "title": tip.title,
                "description": tip.description,
                "potential_saving": tip.potential_saving,
                "priority": tip.priority.value,
                "category": tip.category.value
            }
            for tip in report.tips
        ]
    }


@app.get("/api/user/{telegram_id}/duplicates")
async def get_duplicates(telegram_id: int):
    """Получить дубликаты"""
    
    alerts = await detect_duplicates(telegram_id)
    
    return {
        "duplicates": [
            {
                "main": {
                    "id": alert.main_subscription.id,
                    "name": alert.main_subscription.name
                },
                "duplicate": {
                    "id": alert.duplicate_subscription.id,
                    "name": alert.duplicate_subscription.name
                },
                "overlap_type": alert.overlap_type.value,
                "potential_saving": alert.potential_saving,
                "recommendation": alert.recommendation
            }
            for alert in alerts
        ],
        "total_saving": sum(a.potential_saving for a in alerts)
    }


# ============ СТАТИЧЕСКИЕ ФАЙЛЫ ДЛЯ MINI APP ============

# Раскомментировать когда будут готовы файлы webapp
# app.mount("/app", StaticFiles(directory="webapp", html=True), name="webapp")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)