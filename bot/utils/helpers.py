from datetime import date, datetime, timedelta
from typing import Optional
from ..models import BillingCycle

def format_price(price: float, currency: str = "RUB") -> str:
    """Форматирование цены"""
    if currency == "RUB":
        return f"{price:,.0f}₽".replace(",", " ")
    elif currency == "USD":
        return f"${price:,.2f}"
    elif currency == "EUR":
        return f"€{price:,.2f}"
    return f"{price:,.2f} {currency}"

def format_date(d: date, include_year: bool = True) -> str:
    """Форматирование даты"""
    if include_year:
        return d.strftime("%d.%m.%Y")
    return d.strftime("%d.%m")

def format_date_relative(d: date) -> str:
    """Относительное форматирование даты"""
    today = date.today()
    diff = (d - today).days
    
    if diff == 0:
        return "сегодня"
    elif diff == 1:
        return "завтра"
    elif diff == -1:
        return "вчера"
    elif diff > 1 and diff <= 7:
        return f"через {diff} дн."
    elif diff < -1 and diff >= -7:
        return f"{abs(diff)} дн. назад"
    else:
        return format_date(d, include_year=d.year != today.year)

def get_cycle_name(cycle: BillingCycle, short: bool = False) -> str:
    """Получить название периода"""
    if short:
        names = {
            BillingCycle.WEEKLY: "/нед",
            BillingCycle.MONTHLY: "/мес",
            BillingCycle.QUARTERLY: "/квартал",
            BillingCycle.YEARLY: "/год",
            BillingCycle.LIFETIME: ""
        }
    else:
        names = {
            BillingCycle.WEEKLY: "еженедельно",
            BillingCycle.MONTHLY: "ежемесячно",
            BillingCycle.QUARTERLY: "раз в квартал",
            BillingCycle.YEARLY: "ежегодно",
            BillingCycle.LIFETIME: "навсегда"
        }
    return names.get(cycle, "")

def calculate_monthly_price(price: float, cycle: BillingCycle) -> float:
    """Расчёт месячной стоимости"""
    multipliers = {
        BillingCycle.WEEKLY: 4.33,
        BillingCycle.MONTHLY: 1,
        BillingCycle.QUARTERLY: 1/3,
        BillingCycle.YEARLY: 1/12,
        BillingCycle.LIFETIME: 0
    }
    return price * multipliers.get(cycle, 1)

def calculate_yearly_price(price: float, cycle: BillingCycle) -> float:
    """Расчёт годовой стоимости"""
    return calculate_monthly_price(price, cycle) * 12

def days_until(target_date: date) -> int:
    """Дней до даты"""
    return (target_date - date.today()).days

def pluralize(n: int, forms: tuple) -> str:
    """
    Склонение слов
    forms = ("день", "дня", "дней")
    """
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return forms[1]
    return forms[2]

def format_days(days: int) -> str:
    """Форматирование дней"""
    return f"{days} {pluralize(days, ('день', 'дня', 'дней'))}"

def get_status_emoji(status_value: str, is_trial: bool = False) -> str:
    """Эмодзи статуса"""
    if is_trial:
        return "⏱️"
    return {
        "active": "✅",
        "paused": "⏸️",
        "cancelled": "❌"
    }.get(status_value, "❓")

def truncate(text: str, max_length: int = 30) -> str:
    """Обрезка текста"""
    if len(text) <= max_length:
        return text
    return text[:max_length-1] + "…"