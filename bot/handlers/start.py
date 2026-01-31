from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from ..database import get_or_create_user, get_monthly_spending, get_user_subscriptions
from ..keyboards.inline import get_main_menu_keyboard
from ..keyboards.reply import get_main_reply_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start"""
    await state.clear()
    
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    welcome_text = f"""
👋 Привет, {message.from_user.first_name}!

Я помогу тебе управлять подписками и экономить деньги 💰

🔄 **Что я умею:**
• Отслеживать все твои подписки
• Напоминать о списаниях заранее
• Находить дубликаты и переплаты
• Показывать аналитику расходов
• Напоминать отменить триал

📱 Начни с добавления своих подписок!
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await message.answer(
        "Выбери действие:",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("menu"))
@router.message(F.text == "🏠 Меню")
async def cmd_menu(message: Message, state: FSMContext):
    """Главное меню"""
    await state.clear()
    
    user = await get_or_create_user(message.from_user.id)
    subscriptions = await get_user_subscriptions(message.from_user.id)
    monthly = await get_monthly_spending(message.from_user.id)
    
    if subscriptions:
        stats_text = f"""
📊 **Твоя статистика:**
• Активных подписок: {len(subscriptions)}
• Месячные траты: {monthly:,.0f}₽
• В год: {monthly * 12:,.0f}₽
"""
    else:
        stats_text = "У тебя пока нет подписок. Добавь первую! 👇"
    
    await message.answer(
        stats_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    subscriptions = await get_user_subscriptions(callback.from_user.id)
    monthly = await get_monthly_spending(callback.from_user.id)
    
    if subscriptions:
        stats_text = f"""
📊 **Твоя статистика:**
• Активных подписок: {len(subscriptions)}
• Месячные траты: {monthly:,.0f}₽
• В год: {monthly * 12:,.0f}₽
"""
    else:
        stats_text = "У тебя пока нет подписок. Добавь первую! 👇"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
📖 **Справка по боту**

**Команды:**
/start — Начать работу
/menu — Главное меню
/add — Добавить подписку
/list — Список подписок
/stats — Статистика расходов
/settings — Настройки
/help — Эта справка

**Возможности:**
🔄 **Детектор дубликатов** — найдёт пересекающиеся подписки (например, Яндекс Плюс включает Яндекс Музыку)

⏱️ **Трекер триалов** — напомнит отменить пробный период до списания

📋 **Инструкции отмены** — пошаговые гайды по отмене каждого сервиса

🧠 **Умный анализ** — советы по оптимизации расходов

📊 **Отчёты** — красивая аналитика по тратам

💡 Есть вопросы? Пиши @support
"""
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Быстрая статистика"""
    from ..keyboards.inline import get_analytics_keyboard
    
    subscriptions = await get_user_subscriptions(message.from_user.id)
    monthly = await get_monthly_spending(message.from_user.id)
    
    if not subscriptions:
        await message.answer(
            "У тебя пока нет подписок. Добавь первую!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    text = f"""
📊 **Статистика расходов**

💳 Активных подписок: **{len(subscriptions)}**
📅 В месяц: **{monthly:,.0f}₽**
📆 В год: **{monthly * 12:,.0f}₽**

За 5 лет ты потратишь: **{monthly * 60:,.0f}₽** 😱
"""
    
    await message.answer(
        text,
        reply_markup=get_analytics_keyboard(),
        parse_mode="Markdown"
    )