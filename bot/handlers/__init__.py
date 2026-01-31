from aiogram import Router
from . import start, subscriptions, analytics, reminders, payment, settings, duplicates

def setup_routers() -> Router:
    """Настройка всех роутеров"""
    router = Router()
    
    router.include_router(start.router)
    router.include_router(subscriptions.router)
    router.include_router(duplicates.router)  # Новый!
    router.include_router(analytics.router)
    router.include_router(reminders.router)
    router.include_router(payment.router)
    router.include_router(settings.router)
    
    return router