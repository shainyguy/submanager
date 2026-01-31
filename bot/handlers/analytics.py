from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import date

from ..services.smart_analytics import (
    generate_full_report, generate_smart_tips,
    get_spending_forecast, get_comparison_stats,
    get_priority_emoji, get_category_emoji,
    TipPriority, TipCategory, AnalyticsReport
)
from ..database import (
    get_monthly_spending, get_yearly_spending,
    get_spending_by_category, get_user_subscriptions, is_premium
)
from ..keyboards.inline import get_analytics_keyboard, get_main_menu_keyboard, get_back_keyboard
from ..config import config

router = Router()


@router.callback_query(F.data == "analytics")
async def show_analytics_menu(callback: CallbackQuery):
    """Главное меню аналитики"""
    
    report = await generate_full_report(callback.from_user.id)
    
    if report.subscriptions_count == 0:
        text = """
📊 <b>Аналитика</b>

У тебя пока нет подписок для анализа.
Добавь свои подписки, чтобы увидеть статистику!
"""
        await callback.message.edit_text(
            text, 
            reply_markup=get_back_keyboard("add_subscription")
        )
        await callback.answer()
        return
    
    text = f"""
📊 <b>Аналитика подписок</b>

💰 <b>Расходы:</b>
• В месяц: <b>{report.total_monthly:,.0f}₽</b>
• В год: <b>{report.total_yearly:,.0f}₽</b>

📋 <b>Подписки:</b>
• Всего: {report.subscriptions_count}
• Активных: {report.active_count}
• На паузе: {report.paused_count}
• Триалов: {report.trials_count}

💡 Советов для оптимизации: <b>{len(report.tips)}</b>
"""
    
    if report.tips:
        potential_saving = sum(t.potential_saving for t in report.tips if t.potential_saving > 0)
        if potential_saving > 0:
            text += f"\n💸 Потенциальная экономия: <b>{potential_saving:,.0f}₽/мес</b>"
    
    await callback.message.edit_text(text, reply_markup=get_analytics_keyboard())
    await callback.answer()


@router.callback_query(F.data == "report_monthly")
async def show_monthly_report(callback: CallbackQuery):
    """Месячный отчёт"""
    
    report = await generate_full_report(callback.from_user.id)
    
    text = f"""
📊 <b>Месячный отчёт</b>

💰 <b>Общие расходы: {report.total_monthly:,.0f}₽/мес</b>

"""
    
    # Разбивка по категориям
    if report.by_category:
        text += "📂 <b>По категориям:</b>\n"
        for cat in report.by_category[:6]:
            bar = "█" * int(cat.percent / 10) + "░" * (10 - int(cat.percent / 10))
            text += f"{cat.emoji} {cat.category_name}\n"
            text += f"   {bar} {cat.percent:.0f}% ({cat.amount:,.0f}₽)\n"
        text += "\n"
    
    # Топ расходов
    if report.most_expensive:
        text += f"📈 <b>Самая дорогая:</b> {report.most_expensive.name} "
        text += f"({report.most_expensive.price:,.0f}₽)\n"
    
    if report.cheapest:
        text += f"📉 <b>Самая дешёвая:</b> {report.cheapest.name} "
        text += f"({report.cheapest.price:,.0f}₽)\n"
    
    text += f"\n📍 <b>Средняя подписка:</b> {report.avg_subscription_price:,.0f}₽"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Годовой отчёт", callback_data="report_yearly")
    )
    builder.row(
        InlineKeyboardButton(text="🧠 Умные советы", callback_data="smart_tips")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="analytics")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "report_yearly")
async def show_yearly_report(callback: CallbackQuery):
    """Годовой отчёт"""
    
    report = await generate_full_report(callback.from_user.id)
    forecast = await get_spending_forecast(callback.from_user.id)
    
    text = f"""
📈 <b>Годовой отчёт</b>

💰 <b>Прогноз расходов:</b>
• В месяц: {report.total_monthly:,.0f}₽
• В квартал: {forecast['quarterly']:,.0f}₽
• В год: <b>{report.total_yearly:,.0f}₽</b>

🔮 <b>Долгосрочный прогноз:</b>
• За 5 лет: {forecast['five_years']:,.0f}₽
• За 10 лет: {forecast['ten_years']:,.0f}₽

"""
    
    # Эквиваленты
    text += "🛒 <b>На эти деньги за год можно купить:</b>\n"
    for equiv in forecast['yearly_equivalents']:
        if equiv['count'] >= 0.5:
            text += f"• {equiv['name']}: ~{equiv['count']:.1f} шт.\n"
    
    # Сравнение
    stats = await get_comparison_stats(callback.from_user.id)
    text += f"\n📊 <b>Сравнение со средним:</b>\n"
    text += f"Твои траты {stats['position']}\n"
    
    if stats['diff_percent'] > 0:
        text += f"На {abs(stats['diff_percent']):.0f}% больше среднего"
    elif stats['diff_percent'] < 0:
        text += f"На {abs(stats['diff_percent']):.0f}% меньше среднего"
    else:
        text += "Ровно на среднем уровне"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Месячный", callback_data="report_monthly"),
        InlineKeyboardButton(text="📂 Категории", callback_data="report_categories")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="analytics")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "report_categories")
async def show_categories_report(callback: CallbackQuery):
    """Отчёт по категориям"""
    
    report = await generate_full_report(callback.from_user.id)
    
    if not report.by_category:
        await callback.answer("Нет данных по категориям", show_alert=True)
        return
    
    text = "📂 <b>Расходы по категориям</b>\n\n"
    
    # Визуализация
    max_amount = max(c.amount for c in report.by_category) if report.by_category else 1
    
    for cat in report.by_category:
        bar_length = int((cat.amount / max_amount) * 10) if max_amount > 0 else 0
        bar = "█" * bar_length + "░" * (10 - bar_length)
        
        text += f"{cat.emoji} <b>{cat.category_name}</b>\n"
        text += f"   {bar}\n"
        text += f"   {cat.amount:,.0f}₽/мес • {cat.subscriptions_count} подписок • {cat.percent:.0f}%\n\n"
    
    text += f"💰 <b>Итого: {report.total_monthly:,.0f}₽/мес</b>"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Месячный", callback_data="report_monthly"),
        InlineKeyboardButton(text="📈 Годовой", callback_data="report_yearly")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="analytics")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "report_trends")
async def show_trends_report(callback: CallbackQuery):
    """Отчёт по трендам"""
    
    # Проверяем премиум для расширенной аналитики
    has_premium = await is_premium(callback.from_user.id)
    
    report = await generate_full_report(callback.from_user.id)
    
    text = """
📉 <b>Тренды расходов</b>

"""
    
    if report.trends:
        for trend in report.trends:
            if trend.direction == "up":
                emoji = "📈"
                change_text = f"+{trend.change_percent:.1f}%"
            elif trend.direction == "down":
                emoji = "📉"
                change_text = f"-{trend.change_percent:.1f}%"
            else:
                emoji = "➡️"
                change_text = "0%"
            
            text += f"{emoji} <b>{trend.period}:</b> {trend.amount:,.0f}₽ ({change_text})\n"
    
    text += """

💡 <b>Анализ:</b>
"""
    
    if report.trends and len(report.trends) >= 2:
        first = report.trends[0]
        last = report.trends[-1]
        
        if first.amount > last.amount:
            growth = ((first.amount / last.amount) - 1) * 100
            text += f"Расходы выросли на {growth:.0f}% за последние месяцы.\n"
            text += "Рекомендуем проверить, все ли подписки нужны."
        elif first.amount < last.amount:
            decrease = ((last.amount / first.amount) - 1) * 100
            text += f"Отлично! Расходы снизились на {decrease:.0f}%.\n"
            text += "Ты на правильном пути к оптимизации!"
        else:
            text += "Расходы стабильны. Но всегда есть что улучшить!"
    
    if not has_premium:
        text += """

🔒 <b>В Премиум-версии:</b>
• Детальные графики по месяцам
• История всех расходов
• Прогнозы на основе трендов
• Экспорт в Excel
"""
    
    builder = InlineKeyboardBuilder()
    
    if not has_premium:
        builder.row(
            InlineKeyboardButton(text="⭐ Получить Премиум", callback_data="premium_info")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="analytics")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "smart_tips")
async def show_smart_tips(callback: CallbackQuery):
    """Умные советы"""
    
    tips = await generate_smart_tips(callback.from_user.id)
    
    if not tips:
        text = """
🧠 <b>Умные советы</b>

✅ Отлично! Твои подписки оптимизированы.
Советов по улучшению пока нет.

Продолжай отслеживать расходы!
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("analytics"))
        await callback.answer()
        return
    
    # Считаем общую потенциальную экономию
    total_saving = sum(t.potential_saving for t in tips if t.potential_saving > 0)
    
    text = f"""
🧠 <b>Умные советы</b>

Найдено <b>{len(tips)}</b> советов по оптимизации.
"""
    
    if total_saving > 0:
        text += f"💰 Потенциальная экономия: <b>{total_saving:,.0f}₽/мес</b>\n"
        text += f"📅 В год: <b>{total_saving * 12:,.0f}₽</b>\n"
    
    text += "\n"
    
    # Показываем топ-5 советов
    for i, tip in enumerate(tips[:5], 1):
        priority_emoji = get_priority_emoji(tip.priority)
        cat_emoji = get_category_emoji(tip.category)
        
        text += f"{priority_emoji} <b>{tip.title}</b>\n"
        text += f"   {tip.description}\n"
        if tip.potential_saving > 0:
            text += f"   💰 Экономия: ~{tip.potential_saving:,.0f}₽/мес\n"
        text += "\n"
    
    if len(tips) > 5:
        text += f"\n<i>...и ещё {len(tips) - 5} советов</i>"
    
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки действий для советов с action_callback
    for tip in tips[:3]:
        if tip.action_callback and tip.action_text:
            builder.row(
                InlineKeyboardButton(
                    text=f"➡️ {tip.action_text}",
                    callback_data=tip.action_callback
                )
            )
    
    builder.row(
        InlineKeyboardButton(text="📊 Вся аналитика", callback_data="analytics")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Меню", callback_data="back_to_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "export_data")
async def export_data(callback: CallbackQuery):
    """Экспорт данных (Премиум)"""
    
    has_premium = await is_premium(callback.from_user.id)
    
    if not has_premium:
        text = """
📤 <b>Экспорт данных</b>

Эта функция доступна в Премиум-версии.

✨ <b>Что получите:</b>
• Выгрузка в Excel/CSV
• Полная история подписок
• Аналитика за всё время
"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⭐ Получить Премиум", callback_data="premium_info")
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="analytics")
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return
    
    # Для премиум пользователей — генерируем отчёт
    subscriptions = await get_user_subscriptions(callback.from_user.id)
    report = await generate_full_report(callback.from_user.id)
    
    # Формируем текстовый отчёт
    report_text = "📊 ОТЧЁТ ПО ПОДПИСКАМ\n"
    report_text += f"Дата: {date.today().strftime('%d.%m.%Y')}\n"
    report_text += "=" * 40 + "\n\n"
    
    report_text += f"ОБЩАЯ СТАТИСТИКА\n"
    report_text += f"Подписок: {report.subscriptions_count}\n"
    report_text += f"В месяц: {report.total_monthly:,.0f}₽\n"
    report_text += f"В год: {report.total_yearly:,.0f}₽\n\n"
    
    report_text += "СПИСОК ПОДПИСОК\n"
    report_text += "-" * 40 + "\n"
    
    for sub in subscriptions:
        status = "✓" if sub.status.value == "active" else "⏸" if sub.status.value == "paused" else "✗"
        report_text += f"{status} {sub.name}: {sub.price:,.0f}₽\n"
    
    # Отправляем как документ
    from aiogram.types import BufferedInputFile
    
    file = BufferedInputFile(
        report_text.encode('utf-8'),
        filename=f"subscriptions_report_{date.today().strftime('%Y%m%d')}.txt"
    )
    
    await callback.message.answer_document(
        file,
        caption="📤 Твой отчёт по подпискам"
    )
    await callback.answer("Отчёт сформирован!")


@router.callback_query(F.data == "compare_with_average")
async def compare_with_average(callback: CallbackQuery):
    """Сравнение со средними показателями"""
    
    stats = await get_comparison_stats(callback.from_user.id)
    
    text = f"""
📊 <b>Сравнение со средним пользователем</b>

💰 <b>Расходы:</b>
• Твои: {stats['your_monthly']:,.0f}₽/мес
• Средние: {stats['avg_monthly']:,.0f}₽/мес
• Разница: {'+' if stats['diff_monthly'] >= 0 else ''}{stats['diff_monthly']:,.0f}₽

📋 <b>Количество подписок:</b>
• У тебя: {stats['your_count']}
• В среднем: {stats['avg_count']}

📈 <b>Вывод:</b>
Ты тратишь <b>{stats['position']}</b>
"""
    
    if stats['diff_percent'] > 20:
        text += "\n💡 Возможно, стоит пересмотреть некоторые подписки."
    elif stats['diff_percent'] < -20:
        text += "\n🎉 Отлично! Ты экономишь лучше большинства!"
    else:
        text += "\n👍 Твои расходы в пределах нормы."
    
    # Инфографика
    text += "\n\n📊 <b>Где ты на шкале:</b>\n"
    
    # Позиция на шкале от 0 до 5000
    position = min(max(stats['your_monthly'] / 5000, 0), 1)
    avg_position = stats['avg_monthly'] / 5000
    
    scale = ["░"] * 20
    your_pos = int(position * 19)
    avg_pos = int(avg_position * 19)
    
    scale[avg_pos] = "▽"  # Средний
    scale[your_pos] = "●"  # Ты
    
    text += f"0₽ {''.join(scale)} 5000₽\n"
    text += f"   ▽ = среднее, ● = ты"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("analytics"))
    await callback.answer()