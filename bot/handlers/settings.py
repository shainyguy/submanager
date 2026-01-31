from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from ..database import get_user, async_session, is_premium
from ..models import User
from ..keyboards.inline import get_settings_keyboard, get_premium_keyboard, get_back_keyboard
from sqlalchemy import select

router = Router()


class SettingsState(StatesGroup):
    """Состояния настроек"""
    entering_notify_days = State()
    entering_notify_time = State()
    entering_timezone = State()


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    """Показать настройки"""
    await state.clear()
    
    user = await get_user(callback.from_user.id)
    
    premium_status = "✅ Активен" if await is_premium(callback.from_user.id) else "❌ Нет"
    
    text = f"""
⚙️ <b>Настройки</b>

👤 <b>Профиль:</b>
• Имя: {user.first_name or 'Не указано'}
• Username: @{user.username or 'не указан'}

🔔 <b>Уведомления:</b>
• За сколько дней: {user.notify_before_days}
• Время отправки: {user.notify_time}
• Месячные отчёты: {'✅' if user.notify_monthly_report else '❌'}

🌍 <b>Регион:</b>
• Часовой пояс: {user.timezone}

⭐ <b>Премиум:</b> {premium_status}
"""
    
    if user.total_saved and user.total_saved > 0:
        text += f"\n💰 <b>Сэкономлено:</b> {user.total_saved:,.0f}₽"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(user)
    )
    await callback.answer()


@router.callback_query(F.data == "setting_notify_days")
async def change_notify_days(callback: CallbackQuery, state: FSMContext):
    """Изменить за сколько дней уведомлять"""
    
    text = """
🔔 <b>За сколько дней напоминать?</b>

Выбери, за сколько дней до списания отправлять уведомление:
"""
    
    builder = InlineKeyboardBuilder()
    
    for days in [1, 2, 3, 5, 7, 14]:
        builder.add(
            InlineKeyboardButton(
                text=f"{days} дн.",
                callback_data=f"set_notify_days:{days}"
            )
        )
    
    builder.adjust(3, 3)
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("set_notify_days:"))
async def save_notify_days(callback: CallbackQuery):
    """Сохранить настройку дней"""
    days = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.notify_before_days = days
            await session.commit()
    
    await callback.answer(f"✅ Буду напоминать за {days} дн.")
    
    # Возвращаемся в настройки
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        "⚙️ Настройки обновлены!",
        reply_markup=get_settings_keyboard(user)
    )


@router.callback_query(F.data == "setting_notify_time")
async def change_notify_time(callback: CallbackQuery, state: FSMContext):
    """Изменить время уведомлений"""
    
    text = """
⏰ <b>Время уведомлений</b>

Выбери удобное время для получения напоминаний:
"""
    
    builder = InlineKeyboardBuilder()
    
    times = ["08:00", "09:00", "10:00", "12:00", "14:00", "18:00", "20:00", "21:00"]
    
    for time in times:
        builder.add(
            InlineKeyboardButton(
                text=time,
                callback_data=f"set_notify_time:{time}"
            )
        )
    
    builder.adjust(4, 4)
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("set_notify_time:"))
async def save_notify_time(callback: CallbackQuery):
    """Сохранить время уведомлений"""
    time = callback.data.split(":")[1]
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.notify_time = time
            await session.commit()
    
    await callback.answer(f"✅ Уведомления в {time}")
    
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        "⚙️ Настройки обновлены!",
        reply_markup=get_settings_keyboard(user)
    )


@router.callback_query(F.data == "setting_toggle_reports")
async def toggle_monthly_reports(callback: CallbackQuery):
    """Переключить месячные отчёты"""
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.notify_monthly_report = not user.notify_monthly_report
            new_status = user.notify_monthly_report
            await session.commit()
    
    status_text = "включены" if new_status else "отключены"
    await callback.answer(f"Месячные отчёты {status_text}")
    
    user = await get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(user)
    )


@router.callback_query(F.data == "setting_timezone")
async def change_timezone(callback: CallbackQuery):
    """Изменить часовой пояс"""
    
    text = """
🌍 <b>Часовой пояс</b>

Выбери свой часовой пояс:
"""
    
    builder = InlineKeyboardBuilder()
    
    timezones = [
        ("🇷🇺 Москва (МСК)", "Europe/Moscow"),
        ("🇷🇺 Калининград (МСК-1)", "Europe/Kaliningrad"),
        ("🇷🇺 Самара (МСК+1)", "Europe/Samara"),
        ("🇷🇺 Екатеринбург (МСК+2)", "Asia/Yekaterinburg"),
        ("🇷🇺 Омск (МСК+3)", "Asia/Omsk"),
        ("🇷🇺 Красноярск (МСК+4)", "Asia/Krasnoyarsk"),
        ("🇷🇺 Иркутск (МСК+5)", "Asia/Irkutsk"),
        ("🇷🇺 Владивосток (МСК+7)", "Asia/Vladivostok"),
        ("🇧🇾 Минск", "Europe/Minsk"),
        ("🇰🇿 Алматы", "Asia/Almaty"),
    ]
    
    for name, tz in timezones:
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=f"set_timezone:{tz}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("set_timezone:"))
async def save_timezone(callback: CallbackQuery):
    """Сохранить часовой пояс"""
    timezone = callback.data.split(":", 1)[1]
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.timezone = timezone
            await session.commit()
    
    await callback.answer("✅ Часовой пояс обновлён")
    
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        "⚙️ Настройки обновлены!",
        reply_markup=get_settings_keyboard(user)
    )


@router.callback_query(F.data == "premium_info")
async def show_premium_info(callback: CallbackQuery):
    """Информация о премиуме"""
    
    has_premium = await is_premium(callback.from_user.id)
    
    if has_premium:
        user = await get_user(callback.from_user.id)
        
        if user.premium_type.value == "lifetime":
            status_text = "♾️ Навсегда"
        elif user.premium_expires:
            days_left = (user.premium_expires.date() - date.today()).days
            status_text = f"До {user.premium_expires.strftime('%d.%m.%Y')} ({days_left} дн.)"
        else:
            status_text = "Активен"
        
        text = f"""
⭐ <b>Премиум статус</b>

✅ Премиум активен!
📅 {status_text}

🎁 <b>Твои преимущества:</b>
• Безлимит подписок
• Расширенная аналитика
• Детальные отчёты
• Экспорт данных
• Приоритетная поддержка
• Без рекламы

Спасибо, что поддерживаешь проект! 💜
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("settings"))
    else:
        text = f"""
⭐ <b>Премиум подписка</b>

Разблокируй все возможности бота!

🎁 <b>Что получишь:</b>
• 📋 Безлимит подписок (сейчас: 5)
• 📊 Расширенная аналитика
• 📈 Детальные графики и тренды
• 📤 Экспорт в Excel/CSV
• 🔔 Приоритетные уведомления
• 🎨 Кастомизация отчётов
• 💬 Приоритетная поддержка

💡 <b>Без давления!</b>
Бесплатная версия тоже отлично работает.
Премиум — для тех, кто хочет максимум возможностей.

Выбери удобный вариант:
"""
        await callback.message.edit_text(text, reply_markup=get_premium_keyboard())
    
    await callback.answer()