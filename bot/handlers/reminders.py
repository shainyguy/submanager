from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import date, timedelta

from ..services.trial_tracker import (
    get_trial_alerts, get_trials_summary, format_trial_reminder,
    get_urgency_emoji, TrialUrgency, calculate_trial_savings
)
from ..database import (
    get_user_subscriptions, get_upcoming_billings, 
    get_user, update_subscription
)
from ..keyboards.inline import get_main_menu_keyboard, get_back_keyboard

router = Router()


@router.callback_query(F.data == "reminders")
async def show_reminders(callback: CallbackQuery):
    """Показать напоминания"""
    
    user = await get_user(callback.from_user.id)
    
    # Получаем ближайшие списания
    upcoming = await get_upcoming_billings(callback.from_user.id, days=7)
    
    # Получаем триалы
    trial_summary = await get_trials_summary(callback.from_user.id)
    
    text = f"""
🔔 <b>Напоминания</b>

⚙️ Уведомления за: <b>{user.notify_before_days} дн.</b> до списания
⏰ Время отправки: <b>{user.notify_time}</b>

"""
    
    # Ближайшие списания
    if upcoming:
        text += f"💳 <b>Ближайшие списания ({len(upcoming)}):</b>\n"
        total_upcoming = 0
        for sub in upcoming[:5]:
            days = (sub.next_billing_date - date.today()).days
            emoji = "🔴" if days <= 1 else "🟡" if days <= 3 else "🟢"
            text += f"{emoji} {sub.name}: {sub.price:,.0f}₽ "
            if days == 0:
                text += "(сегодня!)\n"
            elif days == 1:
                text += "(завтра)\n"
            else:
                text += f"(через {days} дн.)\n"
            total_upcoming += sub.price
        text += f"\n💰 Итого скоро: <b>{total_upcoming:,.0f}₽</b>\n"
    else:
        text += "💳 Ближайших списаний нет ✅\n"
    
    text += "\n"
    
    # Триалы
    text += f"⏱️ <b>Пробные периоды:</b>\n{trial_summary['message']}\n"
    
    if trial_summary['total'] > 0:
        text += f"💸 Потенциальные списания: {trial_summary['potential_charges']:,.0f}₽\n"
    
    builder = InlineKeyboardBuilder()
    
    if trial_summary['total'] > 0:
        builder.row(
            InlineKeyboardButton(text="⏱️ Подробнее о триалах", callback_data="trials_detail")
        )
    
    builder.row(
        InlineKeyboardButton(text="📅 Календарь списаний", callback_data="billing_calendar")
    )
    
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки уведомлений", callback_data="settings")
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "trials_detail")
async def show_trials_detail(callback: CallbackQuery):
    """Подробная информация о триалах"""
    
    alerts = await get_trial_alerts(callback.from_user.id, days_ahead=30)
    
    if not alerts:
        text = """
⏱️ <b>Пробные периоды</b>

У тебя нет активных триалов 👍

💡 Когда добавляешь подписку с пробным периодом, я напомню отменить до первого списания!
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("reminders"))
        await callback.answer()
        return
    
    total_savings, count = calculate_trial_savings(alerts)
    
    text = f"""
⏱️ <b>Пробные периоды</b>

Активных триалов: <b>{count}</b>
Потенциальные списания: <b>{total_savings:,.0f}₽</b>

"""
    
    for alert in alerts:
        emoji = get_urgency_emoji(alert.urgency)
        text += f"""
{emoji} <b>{alert.subscription.name}</b>
   Осталось: {alert.days_left} дн. (до {alert.subscription.trial_end_date.strftime('%d.%m')})
   После триала: {alert.price_after_trial:,.0f}₽
"""
    
    text += """

💡 <b>Совет:</b> отменяй триалы за 1-2 дня до окончания, чтобы точно успеть!
"""
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки для критичных триалов
    critical = [a for a in alerts if a.urgency in (TrialUrgency.CRITICAL, TrialUrgency.WARNING)]
    for alert in critical[:3]:
        builder.row(
            InlineKeyboardButton(
                text=f"📋 Как отменить {alert.subscription.name[:20]}",
                callback_data=f"cancel_guide:{alert.subscription.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="reminders")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "billing_calendar")
async def show_billing_calendar(callback: CallbackQuery):
    """Календарь списаний на месяц"""
    
    subscriptions = await get_user_subscriptions(callback.from_user.id)
    active_subs = [s for s in subscriptions if s.status.value == "active" and s.next_billing_date]
    
    if not active_subs:
        text = """
📅 <b>Календарь списаний</b>

У тебя нет активных подписок с запланированными списаниями.
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("reminders"))
        await callback.answer()
        return
    
    # Группируем по неделям
    today = date.today()
    weeks = {
        "this_week": [],
        "next_week": [],
        "this_month": [],
        "later": []
    }
    
    for sub in active_subs:
        days_until = (sub.next_billing_date - today).days
        
        if days_until < 0:
            continue
        elif days_until <= 7:
            weeks["this_week"].append(sub)
        elif days_until <= 14:
            weeks["next_week"].append(sub)
        elif days_until <= 30:
            weeks["this_month"].append(sub)
        else:
            weeks["later"].append(sub)
    
    text = "📅 <b>Календарь списаний</b>\n\n"
    
    if weeks["this_week"]:
        total = sum(s.price for s in weeks["this_week"])
        text += f"📍 <b>Эта неделя</b> ({total:,.0f}₽):\n"
        for sub in sorted(weeks["this_week"], key=lambda x: x.next_billing_date):
            days = (sub.next_billing_date - today).days
            day_text = "сегодня" if days == 0 else "завтра" if days == 1 else sub.next_billing_date.strftime("%d.%m")
            text += f"  • {sub.name}: {sub.price:,.0f}₽ ({day_text})\n"
        text += "\n"
    
    if weeks["next_week"]:
        total = sum(s.price for s in weeks["next_week"])
        text += f"📍 <b>Следующая неделя</b> ({total:,.0f}₽):\n"
        for sub in sorted(weeks["next_week"], key=lambda x: x.next_billing_date):
            text += f"  • {sub.name}: {sub.price:,.0f}₽ ({sub.next_billing_date.strftime('%d.%m')})\n"
        text += "\n"
    
    if weeks["this_month"]:
        total = sum(s.price for s in weeks["this_month"])
        text += f"📍 <b>Позже в этом месяце</b> ({total:,.0f}₽):\n"
        for sub in sorted(weeks["this_month"], key=lambda x: x.next_billing_date)[:5]:
            text += f"  • {sub.name}: {sub.price:,.0f}₽ ({sub.next_billing_date.strftime('%d.%m')})\n"
        if len(weeks["this_month"]) > 5:
            text += f"  ... и ещё {len(weeks['this_month']) - 5}\n"
    
    # Итого за месяц
    all_this_month = weeks["this_week"] + weeks["next_week"] + weeks["this_month"]
    if all_this_month:
        total_month = sum(s.price for s in all_this_month)
        text += f"\n💰 <b>Итого за месяц:</b> {total_month:,.0f}₽"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("reminders"))
    await callback.answer()


@router.callback_query(F.data.startswith("set_reminder:"))
async def set_custom_reminder(callback: CallbackQuery, state: FSMContext):
    """Установить напоминание для подписки"""
    from ..database import get_subscription
    
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    text = f"""
🔔 <b>Напоминание для {subscription.name}</b>

За сколько дней напомнить о списании?
"""
    
    builder = InlineKeyboardBuilder()
    
    for days in [1, 2, 3, 5, 7]:
        builder.add(
            InlineKeyboardButton(
                text=f"{days} дн.",
                callback_data=f"reminder_days:{sub_id}:{days}"
            )
        )
    
    builder.adjust(3, 2)
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"view_sub:{sub_id}")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("reminder_days:"))
async def save_reminder_days(callback: CallbackQuery):
    """Сохранить настройку напоминания"""
    from ..models import Reminder
    from ..database import async_session
    
    parts = callback.data.split(":")
    sub_id = int(parts[1])
    days = int(parts[2])
    
    subscription = await get_subscription(sub_id)
    
    if not subscription or not subscription.next_billing_date:
        await callback.answer("Не удалось установить напоминание", show_alert=True)
        return
    
    remind_date = subscription.next_billing_date - timedelta(days=days)
    
    # Создаём напоминание
    async with async_session() as session:
        reminder = Reminder(
            subscription_id=sub_id,
            remind_date=remind_date,
            remind_type="billing",
            message=f"Через {days} дн. спишется {subscription.price:,.0f}₽ за {subscription.name}"
        )
        session.add(reminder)
        await session.commit()
    
    text = f"""
✅ <b>Напоминание установлено!</b>

{subscription.name}
📅 Напомню: {remind_date.strftime('%d.%m.%Y')}
💰 О списании: {subscription.price:,.0f}₽
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"view_sub:{sub_id}"))
    await callback.answer("Напоминание создано!")