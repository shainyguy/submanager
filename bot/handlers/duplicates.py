from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from ..services.duplicate_detector import (
    detect_duplicates, get_total_potential_savings,
    get_overlap_type_text, get_overlap_type_emoji, OverlapType
)
from ..database import get_subscription, is_premium
from ..keyboards.inline import get_main_menu_keyboard, get_back_keyboard
from ..data.cancel_guides import get_cancel_guide, get_cancel_difficulty_emoji

router = Router()


@router.callback_query(F.data == "duplicates")
async def show_duplicates(callback: CallbackQuery):
    """Показать найденные дубликаты"""
    
    alerts = await detect_duplicates(callback.from_user.id)
    
    if not alerts:
        text = """
🔄 <b>Детектор дубликатов</b>

✅ <b>Отлично!</b> Дубликатов и пересечений не найдено.

Твои подписки оптимизированы, переплат нет 👍

💡 Детектор проверяет:
• Сервисы, включённые в другие подписки
• Похожие сервисы одной категории
• Возможности объединения в бандлы
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    total_saving = await get_total_potential_savings(callback.from_user.id)
    
    text = f"""
🔄 <b>Детектор дубликатов</b>

⚠️ Найдено <b>{len(alerts)}</b> потенциальных проблем!

💰 Возможная экономия: <b>{total_saving:,.0f}₽/мес</b>
📅 В год: <b>{total_saving * 12:,.0f}₽</b>

Выбери проблему для подробностей:
"""
    
    builder = InlineKeyboardBuilder()
    
    for i, alert in enumerate(alerts[:7]):  # Показываем до 7
        emoji = get_overlap_type_emoji(alert.overlap_type)
        name1 = alert.main_subscription.name[:15]
        name2 = alert.duplicate_subscription.name[:15]
        
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {name1} ↔ {name2}",
                callback_data=f"dup_detail:{i}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="📊 Сводка", callback_data="dup_summary"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    # Сохраняем alerts в кэш (в реальном проекте — в Redis или FSM)
    # Пока просто показываем
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "dup_summary")
async def show_duplicates_summary(callback: CallbackQuery):
    """Сводка по дубликатам"""
    
    alerts = await detect_duplicates(callback.from_user.id)
    total_saving = await get_total_potential_savings(callback.from_user.id)
    
    # Группируем по типу
    by_type = {}
    for alert in alerts:
        t = alert.overlap_type
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(alert)
    
    text = f"""
📊 <b>Сводка по оптимизации подписок</b>

💰 <b>Общая возможная экономия:</b>
• В месяц: {total_saving:,.0f}₽
• В год: {total_saving * 12:,.0f}₽
• За 5 лет: {total_saving * 60:,.0f}₽ 🤯

📋 <b>Найденные проблемы:</b>
"""
    
    for overlap_type, type_alerts in by_type.items():
        type_text = get_overlap_type_text(overlap_type)
        type_saving = sum(a.potential_saving for a in type_alerts)
        text += f"\n{type_text}: {len(type_alerts)} шт. ({type_saving:,.0f}₽/мес)"
    
    text += """

💡 <b>Рекомендации:</b>
1. Отмени сервисы, которые уже включены в другие подписки
2. Выбери один сервис из похожих
3. Рассмотри объединение в бандлы
"""
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="duplicates")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("dup_detail:"))
async def show_duplicate_detail(callback: CallbackQuery):
    """Детали дубликата"""
    
    index = int(callback.data.split(":")[1])
    alerts = await detect_duplicates(callback.from_user.id)
    
    if index >= len(alerts):
        await callback.answer("Не найдено", show_alert=True)
        return
    
    alert = alerts[index]
    main_sub = alert.main_subscription
    dup_sub = alert.duplicate_subscription
    
    type_text = get_overlap_type_text(alert.overlap_type)
    
    text = f"""
{type_text}

<b>Основная подписка:</b>
{main_sub.icon or '📦'} {main_sub.name} — {main_sub.price:,.0f}₽

<b>Пересекается с:</b>
{dup_sub.icon or '📦'} {dup_sub.name} — {dup_sub.price:,.0f}₽

💡 <b>Рекомендация:</b>
{alert.recommendation}

💰 <b>Потенциальная экономия:</b> {alert.potential_saving:,.0f}₽/мес
"""
    
    builder = InlineKeyboardBuilder()
    
    # Если есть инструкция по отмене дубликата
    if dup_sub.service_id:
        guide = get_cancel_guide(dup_sub.service_id)
        if guide:
            builder.row(
                InlineKeyboardButton(
                    text=f"📋 Как отменить {dup_sub.name}",
                    callback_data=f"cancel_guide:{dup_sub.id}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(
            text=f"👁️ {main_sub.name}",
            callback_data=f"view_sub:{main_sub.id}"
        ),
        InlineKeyboardButton(
            text=f"👁️ {dup_sub.name}",
            callback_data=f"view_sub:{dup_sub.id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="duplicates")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_guide:"))
async def show_cancel_guide(callback: CallbackQuery):
    """Показать инструкцию по отмене"""
    
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription or not subscription.service_id:
        await callback.answer("Инструкция недоступна", show_alert=True)
        return
    
    guide = get_cancel_guide(subscription.service_id)
    
    if not guide:
        text = f"""
📋 <b>Как отменить {subscription.name}</b>

К сожалению, у нас пока нет подробной инструкции для этого сервиса.

💡 <b>Общие рекомендации:</b>
1. Зайдите в личный кабинет сервиса
2. Найдите раздел "Подписка" или "Настройки"
3. Выберите "Отменить подписку"
4. Если не нашли — обратитесь в поддержку

⚠️ Если подписка оформлена через App Store или Google Play — отменяйте там!
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"view_sub:{sub_id}"))
        await callback.answer()
        return
    
    difficulty_emoji = get_cancel_difficulty_emoji(guide.get("difficulty", "medium"))
    
    text = f"""
📋 <b>Как отменить {guide['name']}</b>

{difficulty_emoji} Сложность: {guide.get('difficulty', 'medium').title()}
⏱️ Время: ~{guide.get('time_minutes', 5)} мин.

<b>Пошаговая инструкция:</b>
"""
    
    for i, step in enumerate(guide.get("steps", []), 1):
        text += f"\n{i}. {step}"
    
    if guide.get("tips"):
        text += "\n\n<b>Полезные советы:</b>"
        for tip in guide["tips"]:
            text += f"\n{tip}"
    
    if guide.get("alternative_steps"):
        text += "\n\n<b>Альтернативный способ:</b>"
        for step in guide["alternative_steps"]:
            text += f"\n• {step}"
    
    builder = InlineKeyboardBuilder()
    
    if guide.get("cancel_url"):
        builder.row(
            InlineKeyboardButton(
                text="🔗 Открыть страницу отмены",
                url=guide["cancel_url"]
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="✅ Отменил!", callback_data=f"mark_cancelled:{sub_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"view_sub:{sub_id}")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("mark_cancelled:"))
async def mark_as_cancelled(callback: CallbackQuery):
    """Отметить подписку как отменённую"""
    from ..database import update_subscription
    from ..models import SubscriptionStatus
    
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    await update_subscription(sub_id, status=SubscriptionStatus.CANCELLED)
    
    # Обновляем статистику экономии пользователя
    from ..database import get_user
    user = await get_user(callback.from_user.id)
    if user:
        from ..database import async_session
        from sqlalchemy import select
        from ..models import User
        
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            db_user = result.scalar_one_or_none()
            if db_user:
                # Добавляем сэкономленное к общей сумме
                from ..database import get_monthly_equivalent
                monthly_saved = get_monthly_equivalent(subscription.price, subscription.billing_cycle)
                db_user.total_saved += monthly_saved * 12  # Годовая экономия
                await session.commit()
    
    text = f"""
✅ <b>Отлично!</b>

{subscription.name} отмечена как отменённая.

💰 Ты сэкономишь примерно <b>{subscription.price:,.0f}₽</b> на следующем списании!

Так держать! 🎉
"""
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer("Подписка отменена! 💪")