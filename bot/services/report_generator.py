"""
📊 Генератор красивых отчётов
"""

from datetime import date, datetime
from typing import List, Optional
from dataclasses import dataclass

from ..models import Subscription, BillingCycle
from ..database import get_user_subscriptions, get_user
from .smart_analytics import generate_full_report, calculate_monthly_price


async def generate_monthly_text_report(telegram_id: int) -> str:
    """Генерация текстового месячного отчёта"""
    
    report = await generate_full_report(telegram_id)
    user = await get_user(telegram_id)
    
    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    current_month = month_names[date.today().month]
    
    text = f"""
╔══════════════════════════════════════╗
║     📊 ОТЧЁТ ЗА {current_month.upper()}
╚══════════════════════════════════════╝

👤 Пользователь: {user.first_name or 'Друг'}
📅 Дата: {date.today().strftime('%d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 ФИНАНСЫ
   
   Месячные расходы:    {report.total_monthly:>10,.0f}₽
   Годовые расходы:     {report.total_yearly:>10,.0f}₽
   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 ПОДПИСКИ

   Всего:              {report.subscriptions_count:>10}
   Активных:           {report.active_count:>10}
   На паузе:           {report.paused_count:>10}
   Триалов:            {report.trials_count:>10}
   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 ПО КАТЕГОРИЯМ

"""
    
    for cat in report.by_category[:5]:
        text += f"   {cat.emoji} {cat.category_name:<15} {cat.amount:>8,.0f}₽  ({cat.percent:.0f}%)\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 МЕТРИКИ

   Средняя подписка:   {report.avg_subscription_price:>10,.0f}₽
"""
    
    if report.most_expensive:
        text += f"   Самая дорогая:     {report.most_expensive.name[:15]:<15}\n"
    
    if report.tips:
        potential = sum(t.potential_saving for t in report.tips if t.potential_saving > 0)
        if potential > 0:
            text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 ПОТЕНЦИАЛ ОПТИМИЗАЦИИ

   Возможная экономия: {potential:>10,.0f}₽/мес
   В год:              {potential * 12:>10,.0f}₽
"""
    
    if user.total_saved and user.total_saved > 0:
        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 ТЫ СЭКОНОМИЛ

   Всего:              {user.total_saved:>10,.0f}₽
"""
    
    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     Сгенерировано ботом SubsManager
              @SubsManagerBot
"""
    
    return text


async def generate_emoji_report(telegram_id: int) -> str:
    """Генерация компактного эмодзи-отчёта для шаринга"""
    
    report = await generate_full_report(telegram_id)
    
    text = f"""
📊 Мои подписки

💰 {report.total_monthly:,.0f}₽/мес | {report.total_yearly:,.0f}₽/год
📋 {report.subscriptions_count} подписок

"""
    
    for cat in report.by_category[:4]:
        bar = "█" * int(cat.percent / 10)
        text += f"{cat.emoji} {bar} {cat.percent:.0f}%\n"
    
    text += f"""
📈 Средняя: {report.avg_subscription_price:,.0f}₽
"""
    
    if report.tips:
        potential = sum(t.potential_saving for t in report.tips if t.potential_saving > 0)
        if potential > 0:
            text += f"💡 Можно сэкономить: {potential:,.0f}₽/мес\n"
    
    text += "\n@SubsManagerBot"
    
    return text


def format_currency(amount: float, currency: str = "RUB") -> str:
    """Форматирование валюты"""
    if currency == "RUB":
        return f"{amount:,.0f}₽".replace(",", " ")
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def generate_progress_bar(value: float, max_value: float, length: int = 10) -> str:
    """Генерация прогресс-бара"""
    if max_value <= 0:
        return "░" * length
    
    filled = int((value / max_value) * length)
    filled = min(filled, length)
    
    return "█" * filled + "░" * (length - filled)


async def generate_subscription_card(subscription: Subscription) -> str:
    """Генерация карточки подписки"""
    
    monthly = calculate_monthly_price(subscription.price, subscription.billing_cycle)
    
    status_emoji = {
        "active": "✅",
        "paused": "⏸️",
        "cancelled": "❌",
        "trial": "⏱️"
    }
    
    cycle_text = {
        BillingCycle.WEEKLY: "нед",
        BillingCycle.MONTHLY: "мес",
        BillingCycle.QUARTERLY: "квартал",
        BillingCycle.YEARLY: "год"
    }
    
    card = f"""
┌─────────────────────────────┐
│ {subscription.icon or '📦'} {subscription.name[:23]:<23} │
├─────────────────────────────┤
│ 💰 {subscription.price:,.0f}₽/{cycle_text.get(subscription.billing_cycle, 'мес'):<20} │
│ 📊 ~{monthly:,.0f}₽/мес                  │
│ {status_emoji.get(subscription.status.value, '❓')} {subscription.status.value.capitalize():<24} │
"""
    
    if subscription.next_billing_date:
        days = (subscription.next_billing_date - date.today()).days
        if days >= 0:
            card += f"│ 📅 Списание через {days} дн.        │\n"
    
    card += "└─────────────────────────────┘"
    
    return card