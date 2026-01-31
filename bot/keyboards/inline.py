from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from ..config import config
from ..config import config
from ..data.subscriptions_catalog import SUBSCRIPTION_CATEGORIES, SUBSCRIPTIONS_CATALOG

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_subscription"),
        InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subscriptions")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Аналитика", callback_data="analytics"),
        InlineKeyboardButton(text="🔔 Напоминания", callback_data="reminders")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Детектор дубликатов", callback_data="duplicates"),
        InlineKeyboardButton(text="⏱️ Триалы", callback_data="trials")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    
    # Mini App кнопка
    if config.WEBAPP_URL:
        builder.row(
            InlineKeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        )
    
    return builder.as_markup()

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Категории подписок"""
    builder = InlineKeyboardBuilder()
    
    for cat_id, cat_name in SUBSCRIPTION_CATEGORIES.items():
        builder.row(
            InlineKeyboardButton(
                text=cat_name,
                callback_data=f"category:{cat_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="✏️ Своя подписка", callback_data="custom_subscription")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data="search_subscription"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_services_keyboard(category: str) -> InlineKeyboardMarkup:
    """Сервисы в категории"""
    builder = InlineKeyboardBuilder()
    
    services = [
        (k, v) for k, v in SUBSCRIPTIONS_CATALOG.items() 
        if v.get("category") == category
    ]
    
    for service_id, service in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{service['icon']} {service['name']} — {service['default_price']}₽",
                callback_data=f"service:{service_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Категории", callback_data="add_subscription")
    )
    
    return builder.as_markup()

def get_billing_cycle_keyboard(service_id: str = None) -> InlineKeyboardMarkup:
    """Выбор периода оплаты"""
    builder = InlineKeyboardBuilder()
    
    cycles = [
        ("weekly", "📅 Еженедельно"),
        ("monthly", "📆 Ежемесячно"),
        ("quarterly", "📊 Раз в 3 месяца"),
        ("yearly", "📅 Ежегодно"),
    ]
    
    for cycle_id, cycle_name in cycles:
        builder.row(
            InlineKeyboardButton(
                text=cycle_name,
                callback_data=f"cycle:{cycle_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="add_subscription")
    )
    
    return builder.as_markup()

def get_subscription_detail_keyboard(subscription_id: int, show_cancel_guide: bool = True) -> InlineKeyboardMarkup:
    """Детали подписки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_sub:{subscription_id}"),
        InlineKeyboardButton(text="⏸️ Пауза", callback_data=f"pause_sub:{subscription_id}")
    )
    
    if show_cancel_guide:
        builder.row(
            InlineKeyboardButton(text="📋 Как отменить", callback_data=f"cancel_guide:{subscription_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔔 Напоминание", callback_data=f"set_reminder:{subscription_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_sub:{subscription_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="my_subscriptions")
    )
    
    return builder.as_markup()

def get_subscriptions_list_keyboard(subscriptions: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Список подписок с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    start = page * per_page
    end = start + per_page
    page_subs = subscriptions[start:end]
    
    for sub in page_subs:
        status_icon = "✅" if sub.status.value == "active" else "⏸️" if sub.status.value == "paused" else "⏱️" if sub.is_trial else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {sub.name} — {sub.price}₽",
                callback_data=f"view_sub:{sub.id}"
            )
        )
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"subs_page:{page-1}")
        )
    if end < len(subscriptions):
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"subs_page:{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_subscription"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_analytics_keyboard() -> InlineKeyboardMarkup:
    """Меню аналитики"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Месячный отчёт", callback_data="report_monthly"),
        InlineKeyboardButton(text="📈 Годовой отчёт", callback_data="report_yearly")
    )
    builder.row(
        InlineKeyboardButton(text="📂 По категориям", callback_data="report_categories"),
        InlineKeyboardButton(text="📉 Тренды", callback_data="report_trends")
    )
    builder.row(
        InlineKeyboardButton(text="🧠 Умные советы", callback_data="smart_tips")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_settings_keyboard(user) -> InlineKeyboardMarkup:
    """Настройки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 Уведомления за {user.notify_before_days} дн.",
            callback_data="setting_notify_days"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"⏰ Время: {user.notify_time}",
            callback_data="setting_notify_time"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📊 Отчёты: {'✅' if user.notify_monthly_report else '❌'}",
            callback_data="setting_toggle_reports"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="setting_timezone")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Премиум", callback_data="premium_info")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_premium_keyboard() -> InlineKeyboardMarkup:
    """Премиум подписка — мягкая, не давящая"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"📅 Месяц — {config.PREMIUM_MONTHLY_PRICE}₽",
            callback_data="buy_premium:monthly"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📆 Год — {config.PREMIUM_YEARLY_PRICE}₽ (выгоднее!)",
            callback_data="buy_premium:yearly"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"♾️ Навсегда — {config.LIFETIME_PRICE}₽",
            callback_data="buy_premium:lifetime"
        )
    )
    builder.row(
        InlineKeyboardButton(text="📜 История платежей", callback_data="payment_history")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings")
    )
    
    return builder.as_markup()


def get_premium_soft_prompt() -> InlineKeyboardMarkup:
    """Мягкое предложение премиума (не давящее)"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✨ Узнать про Premium", callback_data="premium_info")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Подтверждение действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}:{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}:{item_id}")
    )
    
    return builder.as_markup()

def get_back_keyboard(callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)
    )
    return builder.as_markup()

def get_duplicates_keyboard(alerts: list) -> InlineKeyboardMarkup:
    """Список дубликатов"""
    builder = InlineKeyboardBuilder()
    
    for alert in alerts[:5]:
        builder.row(
            InlineKeyboardButton(
                text=f"⚠️ {alert.overlap_type}",
                callback_data=f"view_duplicate:{alert.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()

def get_trials_keyboard(trials: list) -> InlineKeyboardMarkup:
    """Список триалов"""
    builder = InlineKeyboardBuilder()
    
    for trial in trials:
        days_left = (trial.trial_end_date - trial.trial_end_date.today()).days
        builder.row(
            InlineKeyboardButton(
                text=f"⏱️ {trial.name} — {days_left} дн.",
                callback_data=f"view_sub:{trial.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить триал", callback_data="add_trial"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()