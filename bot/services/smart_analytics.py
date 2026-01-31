"""
🧠 Умная аналитика подписок
Анализ паттернов, советы по оптимизации, прогнозы
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from ..models import Subscription, BillingCycle, SubscriptionStatus
from ..database import get_user_subscriptions, get_monthly_spending, get_spending_by_category
from ..data.subscriptions_catalog import SUBSCRIPTION_CATEGORIES


class TipPriority(Enum):
    """Приоритет совета"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TipCategory(Enum):
    """Категория совета"""
    SAVING = "saving"           # Экономия
    OPTIMIZATION = "optimization"  # Оптимизация
    REMINDER = "reminder"       # Напоминание
    INSIGHT = "insight"         # Инсайт


@dataclass
class SmartTip:
    """Умный совет"""
    title: str
    description: str
    potential_saving: float
    priority: TipPriority
    category: TipCategory
    action_text: Optional[str] = None
    action_callback: Optional[str] = None


@dataclass
class SpendingTrend:
    """Тренд расходов"""
    period: str
    amount: float
    change_percent: float
    direction: str  # up, down, stable


@dataclass
class CategoryBreakdown:
    """Разбивка по категории"""
    category_id: str
    category_name: str
    emoji: str
    amount: float
    percent: float
    subscriptions_count: int


@dataclass
class AnalyticsReport:
    """Полный аналитический отчёт"""
    # Основные метрики
    total_monthly: float
    total_yearly: float
    subscriptions_count: int
    active_count: int
    paused_count: int
    trials_count: int
    
    # Разбивка
    by_category: List[CategoryBreakdown]
    
    # Тренды
    trends: List[SpendingTrend]
    
    # Советы
    tips: List[SmartTip]
    
    # Дополнительные метрики
    avg_subscription_price: float
    most_expensive: Optional[Subscription]
    cheapest: Optional[Subscription]
    next_billing_amount: float
    days_until_next_billing: int


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


async def generate_full_report(telegram_id: int) -> AnalyticsReport:
    """Генерация полного аналитического отчёта"""
    
    subscriptions = await get_user_subscriptions(telegram_id)
    
    if not subscriptions:
        return AnalyticsReport(
            total_monthly=0,
            total_yearly=0,
            subscriptions_count=0,
            active_count=0,
            paused_count=0,
            trials_count=0,
            by_category=[],
            trends=[],
            tips=[],
            avg_subscription_price=0,
            most_expensive=None,
            cheapest=None,
            next_billing_amount=0,
            days_until_next_billing=0
        )
    
    # Считаем основные метрики
    active_subs = [s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE]
    paused_subs = [s for s in subscriptions if s.status == SubscriptionStatus.PAUSED]
    trial_subs = [s for s in subscriptions if s.is_trial]
    
    total_monthly = sum(calculate_monthly_price(s.price, s.billing_cycle) for s in active_subs)
    total_yearly = total_monthly * 12
    
    # Разбивка по категориям
    by_category = await _calculate_category_breakdown(active_subs, total_monthly)
    
    # Советы
    tips = await generate_smart_tips(telegram_id, subscriptions)
    
    # Средняя цена
    avg_price = total_monthly / len(active_subs) if active_subs else 0
    
    # Самая дорогая и дешёвая
    if active_subs:
        sorted_by_price = sorted(
            active_subs, 
            key=lambda s: calculate_monthly_price(s.price, s.billing_cycle),
            reverse=True
        )
        most_expensive = sorted_by_price[0]
        cheapest = sorted_by_price[-1]
    else:
        most_expensive = None
        cheapest = None
    
    # Ближайшее списание
    next_billing_amount = 0
    days_until_next = 999
    today = date.today()
    
    for sub in active_subs:
        if sub.next_billing_date:
            days = (sub.next_billing_date - today).days
            if 0 <= days < days_until_next:
                days_until_next = days
                next_billing_amount = sub.price
    
    if days_until_next == 999:
        days_until_next = 0
    
    # Тренды (упрощённо — в реальном проекте нужна история)
    trends = _generate_mock_trends(total_monthly)
    
    return AnalyticsReport(
        total_monthly=round(total_monthly, 2),
        total_yearly=round(total_yearly, 2),
        subscriptions_count=len(subscriptions),
        active_count=len(active_subs),
        paused_count=len(paused_subs),
        trials_count=len(trial_subs),
        by_category=by_category,
        trends=trends,
        tips=tips,
        avg_subscription_price=round(avg_price, 2),
        most_expensive=most_expensive,
        cheapest=cheapest,
        next_billing_amount=next_billing_amount,
        days_until_next_billing=days_until_next
    )


async def _calculate_category_breakdown(
    subscriptions: List[Subscription], 
    total_monthly: float
) -> List[CategoryBreakdown]:
    """Расчёт разбивки по категориям"""
    
    categories = defaultdict(lambda: {"amount": 0, "count": 0})
    
    for sub in subscriptions:
        cat_id = sub.category or "other"
        monthly = calculate_monthly_price(sub.price, sub.billing_cycle)
        categories[cat_id]["amount"] += monthly
        categories[cat_id]["count"] += 1
    
    result = []
    for cat_id, data in sorted(categories.items(), key=lambda x: -x[1]["amount"]):
        cat_info = SUBSCRIPTION_CATEGORIES.get(cat_id, "📦 Другое")
        emoji = cat_info.split()[0] if cat_info else "📦"
        name = cat_info.replace(emoji, "").strip() if cat_info else "Другое"
        
        percent = (data["amount"] / total_monthly * 100) if total_monthly > 0 else 0
        
        result.append(CategoryBreakdown(
            category_id=cat_id,
            category_name=name,
            emoji=emoji,
            amount=round(data["amount"], 2),
            percent=round(percent, 1),
            subscriptions_count=data["count"]
        ))
    
    return result


def _generate_mock_trends(current_monthly: float) -> List[SpendingTrend]:
    """Генерация трендов (заглушка — в реальном проекте нужна история)"""
    
    # Симулируем небольшие изменения
    return [
        SpendingTrend(
            period="Этот месяц",
            amount=current_monthly,
            change_percent=0,
            direction="stable"
        ),
        SpendingTrend(
            period="Прошлый месяц",
            amount=current_monthly * 0.95,
            change_percent=5.3,
            direction="up"
        ),
        SpendingTrend(
            period="3 месяца назад",
            amount=current_monthly * 0.85,
            change_percent=17.6,
            direction="up"
        )
    ]


async def generate_smart_tips(
    telegram_id: int, 
    subscriptions: List[Subscription] = None
) -> List[SmartTip]:
    """Генерация умных советов на основе анализа подписок"""
    
    if subscriptions is None:
        subscriptions = await get_user_subscriptions(telegram_id)
    
    tips = []
    
    if not subscriptions:
        tips.append(SmartTip(
            title="🚀 Начни отслеживать",
            description="Добавь свои подписки, чтобы видеть полную картину расходов",
            potential_saving=0,
            priority=TipPriority.HIGH,
            category=TipCategory.INSIGHT,
            action_text="Добавить подписку",
            action_callback="add_subscription"
        ))
        return tips
    
    active_subs = [s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE]
    total_monthly = sum(calculate_monthly_price(s.price, s.billing_cycle) for s in active_subs)
    
    # 1. Анализ высоких трат
    if total_monthly > 5000:
        tips.append(SmartTip(
            title="💸 Высокие траты на подписки",
            description=f"Ты тратишь {total_monthly:,.0f}₽/мес на подписки. "
                       f"Это {total_monthly * 12:,.0f}₽ в год! Проверь, все ли сервисы ты используешь.",
            potential_saving=total_monthly * 0.2,  # Предполагаем 20% можно сэкономить
            priority=TipPriority.HIGH,
            category=TipCategory.SAVING,
            action_text="Проверить дубликаты",
            action_callback="duplicates"
        ))
    
    # 2. Много подписок в одной категории
    by_category = defaultdict(list)
    for sub in active_subs:
        by_category[sub.category or "other"].append(sub)
    
    for cat_id, cat_subs in by_category.items():
        if len(cat_subs) >= 3:
            cat_name = SUBSCRIPTION_CATEGORIES.get(cat_id, "Другое")
            total_cat = sum(calculate_monthly_price(s.price, s.billing_cycle) for s in cat_subs)
            
            tips.append(SmartTip(
                title=f"📊 Много подписок: {cat_name}",
                description=f"У тебя {len(cat_subs)} подписок в категории «{cat_name}» "
                           f"на сумму {total_cat:,.0f}₽/мес. Возможно, некоторые дублируют друг друга?",
                potential_saving=total_cat * 0.3,
                priority=TipPriority.MEDIUM,
                category=TipCategory.OPTIMIZATION
            ))
    
    # 3. Годовые подписки выгоднее
    monthly_subs = [s for s in active_subs if s.billing_cycle == BillingCycle.MONTHLY]
    expensive_monthly = [s for s in monthly_subs if s.price >= 300]
    
    if expensive_monthly:
        potential_saving = sum(s.price * 0.15 for s in expensive_monthly)  # ~15% экономия на годовых
        tips.append(SmartTip(
            title="📅 Переходи на годовые подписки",
            description=f"У тебя {len(expensive_monthly)} помесячных подписок. "
                       f"Годовая оплата обычно на 15-20% дешевле.",
            potential_saving=potential_saving,
            priority=TipPriority.MEDIUM,
            category=TipCategory.SAVING
        ))
    
    # 4. Неиспользуемые подписки (на паузе долго)
    paused = [s for s in subscriptions if s.status == SubscriptionStatus.PAUSED]
    if paused:
        tips.append(SmartTip(
            title="⏸️ Подписки на паузе",
            description=f"У тебя {len(paused)} подписок на паузе. "
                       f"Если не планируешь возобновлять — отмени их.",
            potential_saving=0,
            priority=TipPriority.LOW,
            category=TipCategory.OPTIMIZATION
        ))
    
    # 5. Триалы, которые скоро закончатся
    trials = [s for s in subscriptions if s.is_trial and s.trial_end_date]
    expiring_trials = [
        s for s in trials 
        if s.trial_end_date and (s.trial_end_date - date.today()).days <= 7
    ]
    
    if expiring_trials:
        total_trial_price = sum(s.price for s in expiring_trials)
        tips.append(SmartTip(
            title="⏱️ Триалы заканчиваются!",
            description=f"{len(expiring_trials)} пробных периодов истекают в ближайшие 7 дней. "
                       f"Если не отменить — спишется {total_trial_price:,.0f}₽",
            potential_saving=total_trial_price,
            priority=TipPriority.HIGH,
            category=TipCategory.REMINDER,
            action_text="Посмотреть триалы",
            action_callback="trials"
        ))
    
    # 6. Совет по объединению (Яндекс)
    yandex_services = [s for s in active_subs if s.service_id and "yandex" in s.service_id]
    has_plus = any(s.service_id == "yandex_plus" for s in yandex_services)
    
    if len(yandex_services) >= 2 and not has_plus:
        tips.append(SmartTip(
            title="🟡 Объедини Яндекс-сервисы",
            description="У тебя несколько подписок Яндекса. "
                       "Яндекс Плюс за 299₽ включает Музыку, Кинопоиск и кэшбэк!",
            potential_saving=150,
            priority=TipPriority.HIGH,
            category=TipCategory.SAVING,
            action_text="Проверить дубликаты",
            action_callback="duplicates"
        ))
    
    # 7. Совет по VPN
    vpn_subs = [s for s in active_subs if s.category == "vpn"]
    if len(vpn_subs) >= 2:
        tips.append(SmartTip(
            title="🔒 Несколько VPN?",
            description="У тебя больше одного VPN-сервиса. Обычно достаточно одного надёжного.",
            potential_saving=sum(calculate_monthly_price(s.price, s.billing_cycle) for s in vpn_subs[1:]),
            priority=TipPriority.MEDIUM,
            category=TipCategory.OPTIMIZATION
        ))
    
    # 8. Большие траты на стриминг
    streaming_subs = [s for s in active_subs if s.category == "streaming"]
    streaming_total = sum(calculate_monthly_price(s.price, s.billing_cycle) for s in streaming_subs)
    
    if streaming_total > 1500:
        tips.append(SmartTip(
            title="🎬 Много стримингов",
            description=f"На видео-сервисы уходит {streaming_total:,.0f}₽/мес. "
                       f"Возможно, стоит чередовать подписки, а не держать все сразу?",
            potential_saving=streaming_total * 0.4,
            priority=TipPriority.MEDIUM,
            category=TipCategory.INSIGHT
        ))
    
    # 9. Правило 50/30/20
    if total_monthly > 0:
        tips.append(SmartTip(
            title="💡 Знаешь правило 50/30/20?",
            description=f"Подписки относятся к «желаниям» (30% бюджета). "
                       f"При доходе 80,000₽ это максимум 24,000₽/мес на все развлечения.",
            potential_saving=0,
            priority=TipPriority.LOW,
            category=TipCategory.INSIGHT
        ))
    
    # Сортируем по приоритету и экономии
    priority_order = {TipPriority.HIGH: 0, TipPriority.MEDIUM: 1, TipPriority.LOW: 2}
    tips.sort(key=lambda t: (priority_order[t.priority], -t.potential_saving))
    
    return tips[:10]  # Максимум 10 советов


def get_priority_emoji(priority: TipPriority) -> str:
    """Эмодзи приоритета"""
    return {
        TipPriority.HIGH: "🔴",
        TipPriority.MEDIUM: "🟡",
        TipPriority.LOW: "🟢"
    }.get(priority, "⚪")


def get_category_emoji(category: TipCategory) -> str:
    """Эмодзи категории совета"""
    return {
        TipCategory.SAVING: "💰",
        TipCategory.OPTIMIZATION: "⚡",
        TipCategory.REMINDER: "🔔",
        TipCategory.INSIGHT: "💡"
    }.get(category, "📌")


async def get_spending_forecast(telegram_id: int) -> Dict:
    """Прогноз расходов на будущее"""
    
    monthly = await get_monthly_spending(telegram_id)
    
    return {
        "monthly": monthly,
        "quarterly": monthly * 3,
        "yearly": monthly * 12,
        "five_years": monthly * 60,
        "ten_years": monthly * 120,
        
        # Что можно купить на эти деньги
        "yearly_equivalents": [
            {"name": "iPhone", "count": round(monthly * 12 / 80000, 1)},
            {"name": "Отпуск", "count": round(monthly * 12 / 100000, 1)},
            {"name": "Ужин в ресторане", "count": round(monthly * 12 / 3000, 1)},
        ]
    }


async def get_comparison_stats(telegram_id: int) -> Dict:
    """Сравнительная статистика (анонимизированная)"""
    
    monthly = await get_monthly_spending(telegram_id)
    subscriptions = await get_user_subscriptions(telegram_id)
    count = len([s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE])
    
    # Средние значения (в реальном проекте — из базы всех пользователей)
    avg_monthly = 2500  # Средние траты
    avg_count = 7  # Среднее количество подписок
    
    return {
        "your_monthly": monthly,
        "avg_monthly": avg_monthly,
        "diff_monthly": monthly - avg_monthly,
        "diff_percent": ((monthly / avg_monthly) - 1) * 100 if avg_monthly > 0 else 0,
        
        "your_count": count,
        "avg_count": avg_count,
        "diff_count": count - avg_count,
        
        "position": "выше среднего" if monthly > avg_monthly else "ниже среднего" if monthly < avg_monthly else "на уровне среднего"
    }