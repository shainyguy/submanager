"""
⏱️ Трекер пробных периодов
Напоминает отменить до списания
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import Subscription, SubscriptionStatus
from ..database import get_user_subscriptions, get_expiring_trials, update_subscription


class TrialUrgency(Enum):
    """Срочность триала"""
    CRITICAL = "critical"      # Сегодня/завтра
    WARNING = "warning"        # 2-3 дня
    UPCOMING = "upcoming"      # 4-7 дней
    SAFE = "safe"              # Более 7 дней


@dataclass
class TrialAlert:
    """Информация о триале"""
    subscription: Subscription
    days_left: int
    urgency: TrialUrgency
    price_after_trial: float
    message: str


def get_urgency(days_left: int) -> TrialUrgency:
    """Определить срочность по дням"""
    if days_left <= 1:
        return TrialUrgency.CRITICAL
    elif days_left <= 3:
        return TrialUrgency.WARNING
    elif days_left <= 7:
        return TrialUrgency.UPCOMING
    return TrialUrgency.SAFE


def get_urgency_emoji(urgency: TrialUrgency) -> str:
    """Эмодзи срочности"""
    return {
        TrialUrgency.CRITICAL: "🔴",
        TrialUrgency.WARNING: "🟡",
        TrialUrgency.UPCOMING: "🟢",
        TrialUrgency.SAFE: "⚪"
    }.get(urgency, "⚪")


async def get_trial_alerts(telegram_id: int, days_ahead: int = 14) -> List[TrialAlert]:
    """
    Получить все триалы, которые заканчиваются в ближайшие N дней
    """
    trials = await get_expiring_trials(telegram_id, days=days_ahead)
    
    alerts = []
    today = date.today()
    
    for trial in trials:
        if not trial.trial_end_date:
            continue
        
        days_left = (trial.trial_end_date - today).days
        urgency = get_urgency(days_left)
        
        # Формируем сообщение
        if days_left <= 0:
            message = f"⚠️ Триал {trial.name} закончился! Проверь, не списались ли деньги"
        elif days_left == 1:
            message = f"🔴 {trial.name} — триал заканчивается ЗАВТРА! Отмени сейчас, если не нужна подписка"
        elif days_left <= 3:
            message = f"🟡 {trial.name} — осталось {days_left} дн. до списания {trial.price:.0f}₽"
        else:
            message = f"🟢 {trial.name} — {days_left} дн. до конца триала"
        
        alerts.append(TrialAlert(
            subscription=trial,
            days_left=days_left,
            urgency=urgency,
            price_after_trial=trial.price,
            message=message
        ))
    
    # Сортируем по срочности
    urgency_order = {
        TrialUrgency.CRITICAL: 0,
        TrialUrgency.WARNING: 1,
        TrialUrgency.UPCOMING: 2,
        TrialUrgency.SAFE: 3
    }
    alerts.sort(key=lambda x: (urgency_order[x.urgency], x.days_left))
    
    return alerts


async def get_critical_trials(telegram_id: int) -> List[TrialAlert]:
    """Получить только критичные триалы (1-2 дня)"""
    all_alerts = await get_trial_alerts(telegram_id, days_ahead=3)
    return [a for a in all_alerts if a.urgency in (TrialUrgency.CRITICAL, TrialUrgency.WARNING)]


async def mark_trial_as_converted(subscription_id: int):
    """Отметить, что триал перешёл в платную подписку"""
    await update_subscription(
        subscription_id,
        is_trial=False,
        trial_end_date=None,
        status=SubscriptionStatus.ACTIVE
    )


async def get_trials_summary(telegram_id: int) -> dict:
    """Получить сводку по триалам"""
    alerts = await get_trial_alerts(telegram_id, days_ahead=30)
    
    if not alerts:
        return {
            "total": 0,
            "critical": 0,
            "warning": 0,
            "potential_charges": 0,
            "message": "У тебя нет активных триалов 👍"
        }
    
    critical = [a for a in alerts if a.urgency == TrialUrgency.CRITICAL]
    warning = [a for a in alerts if a.urgency == TrialUrgency.WARNING]
    
    # Потенциальные списания
    potential = sum(a.price_after_trial for a in alerts)
    
    if critical:
        message = f"🔴 {len(critical)} триал(ов) заканчиваются в ближайшие 1-2 дня!"
    elif warning:
        message = f"🟡 {len(warning)} триал(ов) заканчиваются в ближайшие 3 дня"
    else:
        message = f"🟢 {len(alerts)} триал(ов) активно, всё под контролем"
    
    return {
        "total": len(alerts),
        "critical": len(critical),
        "warning": len(warning),
        "potential_charges": potential,
        "message": message,
        "alerts": alerts
    }


def format_trial_reminder(alert: TrialAlert) -> str:
    """Форматирование напоминания о триале"""
    emoji = get_urgency_emoji(alert.urgency)
    
    text = f"""
{emoji} <b>{alert.subscription.name}</b>

⏱️ Триал заканчивается: <b>{alert.subscription.trial_end_date.strftime('%d.%m.%Y')}</b>
📅 Осталось: <b>{alert.days_left} дн.</b>
💰 После триала: <b>{alert.price_after_trial:,.0f}₽</b>

"""
    
    if alert.urgency == TrialUrgency.CRITICAL:
        text += "⚠️ <b>Срочно отмени, если не планируешь использовать!</b>"
    elif alert.urgency == TrialUrgency.WARNING:
        text += "💡 Самое время решить — оставляешь или отменяешь?"
    else:
        text += "✅ Пока есть время подумать"
    
    return text


def calculate_trial_savings(alerts: List[TrialAlert]) -> Tuple[float, int]:
    """
    Посчитать, сколько можно сэкономить, отменив триалы
    Возвращает (сумма экономии, количество триалов)
    """
    total = sum(a.price_after_trial for a in alerts)
    return (total, len(alerts))