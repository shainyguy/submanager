"""
🔄 Детектор дубликатов подписок
Находит пересечения и переплаты
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..data.subscriptions_catalog import SUBSCRIPTIONS_CATALOG
from ..models import Subscription, BillingCycle
from ..database import get_user_subscriptions

class OverlapType(Enum):
    INCLUDED = "included"           # Один сервис включён в другой
    SIMILAR = "similar"             # Похожие сервисы (одна категория)
    REDUNDANT = "redundant"         # Избыточные (одинаковый функционал)
    FAMILY_UPGRADE = "family"       # Можно объединить в семейную подписку

@dataclass
class DuplicateAlert:
    """Информация о найденном дубликате"""
    main_subscription: Subscription
    duplicate_subscription: Subscription
    overlap_type: OverlapType
    potential_saving: float
    recommendation: str
    priority: int  # 1-5, где 5 — самое важное

# Карта включённых сервисов
INCLUSION_MAP = {
    "yandex_plus": ["yandex_music", "kinopoisk", "yandex_disk_bonus"],
    "yandex_plus_multi": ["yandex_music", "kinopoisk", "yandex_disk_bonus", "amediateka"],
    "sber_prime": ["sber_zvuk", "okko", "sber_disk"],
    "mts_premium": ["mts_music", "kion", "mts_library"],
    "vk_combo": ["vk_music"],
}

# Сервисы одной категории, которые дублируют друг друга
SIMILAR_SERVICES = {
    "music": [
        ["yandex_music", "vk_music", "spotify", "apple_music", "sber_zvuk", "mts_music", "zvuk"],
    ],
    "video": [
        ["kinopoisk", "ivi", "okko", "kion", "premier", "wink", "start", "more_tv"],
    ],
    "books": [
        ["litres", "bookmate", "mybook", "storytel"],
    ],
    "cloud": [
        ["yandex_disk", "mail_cloud", "icloud", "google_one"],
    ],
}

# Рекомендации по объединению
BUNDLE_RECOMMENDATIONS = {
    ("yandex_music", "kinopoisk"): {
        "bundle": "yandex_plus",
        "bundle_price": 299,
        "message": "Яндекс Плюс включает оба сервиса дешевле!"
    },
    ("sber_zvuk", "okko"): {
        "bundle": "sber_prime",
        "bundle_price": 399,
        "message": "СберПрайм включает оба + кэшбэк!"
    },
    ("mts_music", "kion"): {
        "bundle": "mts_premium",
        "bundle_price": 399,
        "message": "МТС Premium включает оба + бонусы связи!"
    },
}


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


async def detect_duplicates(telegram_id: int) -> List[DuplicateAlert]:
    """
    Главная функция: находит все дубликаты и пересечения
    """
    subscriptions = await get_user_subscriptions(telegram_id)
    
    if len(subscriptions) < 2:
        return []
    
    alerts = []
    
    # 1. Проверяем включённые сервисы
    alerts.extend(_check_included_services(subscriptions))
    
    # 2. Проверяем похожие сервисы
    alerts.extend(_check_similar_services(subscriptions))
    
    # 3. Проверяем возможность объединения в бандлы
    alerts.extend(_check_bundle_opportunities(subscriptions))
    
    # Сортируем по приоритету и потенциальной экономии
    alerts.sort(key=lambda x: (-x.priority, -x.potential_saving))
    
    return alerts


def _check_included_services(subscriptions: List[Subscription]) -> List[DuplicateAlert]:
    """Проверяет, не платит ли пользователь за сервис, который уже включён в другую подписку"""
    alerts = []
    
    # Создаём словарь подписок по service_id
    sub_by_service = {s.service_id: s for s in subscriptions if s.service_id}
    
    for sub in subscriptions:
        if not sub.service_id:
            continue
            
        # Проверяем, включает ли эта подписка другие сервисы
        included = INCLUSION_MAP.get(sub.service_id, [])
        
        # Также проверяем поле included_services из каталога
        catalog_info = SUBSCRIPTIONS_CATALOG.get(sub.service_id, {})
        included.extend(catalog_info.get("included_services", []))
        
        for included_service_id in included:
            if included_service_id in sub_by_service:
                duplicate_sub = sub_by_service[included_service_id]
                
                # Считаем экономию
                saving = calculate_monthly_price(duplicate_sub.price, duplicate_sub.billing_cycle)
                
                alerts.append(DuplicateAlert(
                    main_subscription=sub,
                    duplicate_subscription=duplicate_sub,
                    overlap_type=OverlapType.INCLUDED,
                    potential_saving=saving,
                    recommendation=f"💡 {duplicate_sub.name} уже входит в {sub.name}! Можно сэкономить {saving:.0f}₽/мес",
                    priority=5
                ))
    
    return alerts


def _check_similar_services(subscriptions: List[Subscription]) -> List[DuplicateAlert]:
    """Проверяет наличие похожих сервисов одной категории"""
    alerts = []
    
    # Группируем подписки по категориям
    by_category = {}
    for sub in subscriptions:
        if sub.category:
            if sub.category not in by_category:
                by_category[sub.category] = []
            by_category[sub.category].append(sub)
    
    # Проверяем каждую группу
    for category, subs in by_category.items():
        if len(subs) < 2:
            continue
        
        # Ищем пары сервисов, которые дублируют функционал
        for similar_group in SIMILAR_SERVICES.get(category, []):
            found_in_group = [s for s in subs if s.service_id in similar_group]
            
            if len(found_in_group) >= 2:
                # Сортируем по цене — оставляем самый дешёвый
                found_in_group.sort(
                    key=lambda s: calculate_monthly_price(s.price, s.billing_cycle)
                )
                
                cheapest = found_in_group[0]
                for duplicate in found_in_group[1:]:
                    saving = calculate_monthly_price(duplicate.price, duplicate.billing_cycle)
                    
                    alerts.append(DuplicateAlert(
                        main_subscription=cheapest,
                        duplicate_subscription=duplicate,
                        overlap_type=OverlapType.SIMILAR,
                        potential_saving=saving,
                        recommendation=f"🤔 {duplicate.name} и {cheapest.name} — похожие сервисы. Нужны ли оба?",
                        priority=3
                    ))
    
    return alerts


def _check_bundle_opportunities(subscriptions: List[Subscription]) -> List[DuplicateAlert]:
    """Проверяет, можно ли объединить подписки в выгодный бандл"""
    alerts = []
    
    sub_ids = {s.service_id for s in subscriptions if s.service_id}
    sub_by_id = {s.service_id: s for s in subscriptions if s.service_id}
    
    for (service1, service2), bundle_info in BUNDLE_RECOMMENDATIONS.items():
        if service1 in sub_ids and service2 in sub_ids:
            sub1 = sub_by_id[service1]
            sub2 = sub_by_id[service2]
            
            # Считаем текущие траты
            current_cost = (
                calculate_monthly_price(sub1.price, sub1.billing_cycle) +
                calculate_monthly_price(sub2.price, sub2.billing_cycle)
            )
            
            bundle_cost = bundle_info["bundle_price"]
            saving = current_cost - bundle_cost
            
            if saving > 0:
                alerts.append(DuplicateAlert(
                    main_subscription=sub1,
                    duplicate_subscription=sub2,
                    overlap_type=OverlapType.REDUNDANT,
                    potential_saving=saving,
                    recommendation=f"💰 {bundle_info['message']} Экономия: {saving:.0f}₽/мес",
                    priority=4
                ))
    
    return alerts


def get_overlap_type_text(overlap_type: OverlapType) -> str:
    """Получить текстовое описание типа пересечения"""
    return {
        OverlapType.INCLUDED: "🔄 Уже включено",
        OverlapType.SIMILAR: "🔀 Похожие сервисы",
        OverlapType.REDUNDANT: "💰 Можно объединить",
        OverlapType.FAMILY_UPGRADE: "👨‍👩‍👧‍👦 Семейный план выгоднее"
    }.get(overlap_type, "❓ Неизвестно")


def get_overlap_type_emoji(overlap_type: OverlapType) -> str:
    """Эмодзи для типа пересечения"""
    return {
        OverlapType.INCLUDED: "🔄",
        OverlapType.SIMILAR: "🔀",
        OverlapType.REDUNDANT: "💰",
        OverlapType.FAMILY_UPGRADE: "👨‍👩‍👧‍👦"
    }.get(overlap_type, "❓")


async def get_total_potential_savings(telegram_id: int) -> float:
    """Получить общую потенциальную экономию"""
    alerts = await detect_duplicates(telegram_id)
    
    # Учитываем только уникальные дубликаты
    seen = set()
    total = 0.0
    
    for alert in alerts:
        dup_id = alert.duplicate_subscription.id
        if dup_id not in seen:
            seen.add(dup_id)
            total += alert.potential_saving
    
    return total