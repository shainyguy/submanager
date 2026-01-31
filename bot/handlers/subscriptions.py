from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime, date, timedelta
from typing import Optional

from ..states import AddSubscription, EditSubscription, CustomSubscription, SearchSubscription, AddTrial
from ..database import (
    get_or_create_user, add_subscription, get_user_subscriptions,
    get_subscription, update_subscription, delete_subscription,
    get_subscriptions_count, is_premium, get_expiring_trials
)
from ..models import SubscriptionStatus, BillingCycle
from ..keyboards.inline import (
    get_categories_keyboard, get_services_keyboard, get_billing_cycle_keyboard,
    get_subscription_detail_keyboard, get_subscriptions_list_keyboard,
    get_confirm_keyboard, get_back_keyboard, get_main_menu_keyboard,
    get_trials_keyboard
)
from ..keyboards.reply import get_cancel_keyboard, get_skip_keyboard, get_main_reply_keyboard
from ..data.subscriptions_catalog import (
    SUBSCRIPTIONS_CATALOG, SUBSCRIPTION_CATEGORIES,
    get_subscription_by_id, search_subscriptions
)
from ..config import config

router = Router()

# ============ СПИСОК ПОДПИСОК ============

@router.message(Command("list"))
@router.message(F.text == "📋 Подписки")
@router.callback_query(F.data == "my_subscriptions")
async def show_subscriptions(update: Message | CallbackQuery, state: FSMContext):
    """Показать список подписок"""
    await state.clear()
    
    user_id = update.from_user.id
    subscriptions = await get_user_subscriptions(user_id)
    
    if not subscriptions:
        text = """
📋 <b>Мои подписки</b>

У тебя пока нет добавленных подписок.

Добавь свою первую подписку, чтобы начать отслеживать расходы! 👇
"""
        keyboard = get_back_keyboard("add_subscription")
        keyboard.inline_keyboard.insert(0, [
            {"text": "➕ Добавить подписку", "callback_data": "add_subscription"}
        ])
    else:
        # Считаем общую сумму
        total_monthly = 0
        for sub in subscriptions:
            if sub.billing_cycle == BillingCycle.WEEKLY:
                total_monthly += sub.price * 4.33
            elif sub.billing_cycle == BillingCycle.MONTHLY:
                total_monthly += sub.price
            elif sub.billing_cycle == BillingCycle.QUARTERLY:
                total_monthly += sub.price / 3
            elif sub.billing_cycle == BillingCycle.YEARLY:
                total_monthly += sub.price / 12
        
        active_count = len([s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE])
        trial_count = len([s for s in subscriptions if s.is_trial])
        
        text = f"""
📋 <b>Мои подписки</b>

📊 Всего: <b>{len(subscriptions)}</b> подписок
✅ Активных: <b>{active_count}</b>
⏱️ Триалов: <b>{trial_count}</b>

💰 В месяц: <b>{total_monthly:,.0f}₽</b>
📅 В год: <b>{total_monthly * 12:,.0f}₽</b>

Выбери подписку для подробностей:
"""
        keyboard = get_subscriptions_list_keyboard(subscriptions)
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=keyboard)
        await update.answer()
    else:
        await update.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("subs_page:"))
async def subscriptions_page(callback: CallbackQuery):
    """Пагинация списка подписок"""
    page = int(callback.data.split(":")[1])
    subscriptions = await get_user_subscriptions(callback.from_user.id)
    
    keyboard = get_subscriptions_list_keyboard(subscriptions, page=page)
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

# ============ ПРОСМОТР ПОДПИСКИ ============

@router.callback_query(F.data.startswith("view_sub:"))
async def view_subscription(callback: CallbackQuery):
    """Просмотр деталей подписки"""
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    # Форматируем статус
    status_map = {
        SubscriptionStatus.ACTIVE: "✅ Активна",
        SubscriptionStatus.PAUSED: "⏸️ На паузе",
        SubscriptionStatus.CANCELLED: "❌ Отменена",
        SubscriptionStatus.TRIAL: "⏱️ Пробный период"
    }
    status_text = status_map.get(subscription.status, "❓ Неизвестно")
    
    # Форматируем цикл оплаты
    cycle_map = {
        BillingCycle.WEEKLY: "еженедельно",
        BillingCycle.MONTHLY: "ежемесячно",
        BillingCycle.QUARTERLY: "раз в 3 месяца",
        BillingCycle.YEARLY: "ежегодно",
        BillingCycle.LIFETIME: "навсегда"
    }
    cycle_text = cycle_map.get(subscription.billing_cycle, "")
    
    # Расчёт месячной стоимости
    if subscription.billing_cycle == BillingCycle.WEEKLY:
        monthly_cost = subscription.price * 4.33
    elif subscription.billing_cycle == BillingCycle.MONTHLY:
        monthly_cost = subscription.price
    elif subscription.billing_cycle == BillingCycle.QUARTERLY:
        monthly_cost = subscription.price / 3
    elif subscription.billing_cycle == BillingCycle.YEARLY:
        monthly_cost = subscription.price / 12
    else:
        monthly_cost = 0
    
    # Дни до списания
    days_until = None
    if subscription.next_billing_date:
        days_until = (subscription.next_billing_date - date.today()).days
    
    # Формируем текст
    text = f"""
{subscription.icon or '📦'} <b>{subscription.name}</b>

💰 <b>Стоимость:</b> {subscription.price:,.0f}₽ {cycle_text}
📊 <b>В месяц:</b> ~{monthly_cost:,.0f}₽

📍 <b>Статус:</b> {status_text}
"""
    
    if subscription.is_trial and subscription.trial_end_date:
        trial_days = (subscription.trial_end_date - date.today()).days
        text += f"⏱️ <b>Триал до:</b> {subscription.trial_end_date.strftime('%d.%m.%Y')} ({trial_days} дн.)\n"
    
    if days_until is not None and days_until >= 0:
        text += f"📅 <b>Следующее списание:</b> {subscription.next_billing_date.strftime('%d.%m.%Y')}"
        if days_until == 0:
            text += " (сегодня! ⚠️)"
        elif days_until == 1:
            text += " (завтра)"
        elif days_until <= 3:
            text += f" (через {days_until} дн.)"
        text += "\n"
    
    if subscription.category:
        cat_name = SUBSCRIPTION_CATEGORIES.get(subscription.category, subscription.category)
        text += f"📂 <b>Категория:</b> {cat_name}\n"
    
    if subscription.notes:
        text += f"📝 <b>Заметка:</b> {subscription.notes}\n"
    
    # Проверяем, есть ли инструкция по отмене
    service_info = get_subscription_by_id(subscription.service_id) if subscription.service_id else None
    show_cancel = bool(service_info and service_info.get("cancel_url"))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_subscription_detail_keyboard(sub_id, show_cancel_guide=show_cancel)
    )
    await callback.answer()

# ============ ДОБАВЛЕНИЕ ПОДПИСКИ ============

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить")
@router.callback_query(F.data == "add_subscription")
async def start_add_subscription(update: Message | CallbackQuery, state: FSMContext):
    """Начало добавления подписки"""
    await state.clear()
    
    user_id = update.from_user.id
    
     # Проверка лимита для бесплатных пользователей
    if not await is_premium(user_id):
        count = await get_subscriptions_count(user_id)
        if count >= config.FREE_SUBSCRIPTIONS_LIMIT:
            text = f"""
📋 <b>Достигнут лимит подписок</b>

В бесплатной версии можно отслеживать до {config.FREE_SUBSCRIPTIONS_LIMIT} подписок.
У тебя уже {count} — молодец, что следишь за расходами! 👍

<b>Что можно сделать:</b>
• Удалить неактуальные подписки
• Оформить Premium для безлимита

💡 <i>Premium — это не обязательно! 
Бесплатная версия отлично работает для большинства.</i>
"""
            from ..keyboards.inline import get_premium_soft_prompt
            keyboard = get_premium_soft_prompt()
            
            # Добавляем кнопку списка подписок
            from aiogram.types import InlineKeyboardButton
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subscriptions")
            ])
            
            if isinstance(update, CallbackQuery):
                await update.message.edit_text(text, reply_markup=keyboard)
                await update.answer()
            else:
                await update.answer(text, reply_markup=keyboard)
            return
    
    text = """
➕ <b>Добавление подписки</b>

Выбери категорию или воспользуйся поиском:
"""
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=get_categories_keyboard())
        await update.answer()
    else:
        await update.answer(text, reply_markup=get_categories_keyboard())
    
    await state.set_state(AddSubscription.choosing_category)

@router.callback_query(F.data.startswith("category:"), AddSubscription.choosing_category)
async def choose_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории"""
    category = callback.data.split(":")[1]
    
    await state.update_data(category=category)
    
    cat_name = SUBSCRIPTION_CATEGORIES.get(category, category)
    text = f"""
{cat_name}

Выбери сервис или добавь свой:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_services_keyboard(category)
    )
    await state.set_state(AddSubscription.choosing_service)
    await callback.answer()

@router.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    """Выбор сервиса из каталога"""
    service_id = callback.data.split(":")[1]
    service = get_subscription_by_id(service_id)
    
    if not service:
        await callback.answer("Сервис не найден", show_alert=True)
        return
    
    await state.update_data(
        service_id=service_id,
        name=service["name"],
        icon=service.get("icon", "📦"),
        color=service.get("color"),
        category=service.get("category"),
        default_price=service.get("default_price", 0),
        included_services=service.get("included_services", [])
    )
    
    text = f"""
{service.get('icon', '📦')} <b>{service['name']}</b>

{service.get('description', '')}

💰 Стандартная цена: <b>{service.get('default_price', 0)}₽/мес</b>

Введи свою цену (или отправь 0, чтобы использовать стандартную):
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("add_subscription"))
    await callback.message.answer("Введи цену подписки:", reply_markup=get_cancel_keyboard())
    await state.set_state(AddSubscription.entering_price)
    await callback.answer()

@router.message(AddSubscription.entering_price)
async def enter_price(message: Message, state: FSMContext):
    """Ввод цены"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    try:
        price = float(message.text.replace(",", ".").replace("₽", "").strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи корректную цену (число)")
        return
    
    data = await state.get_data()
    
    # Если ввели 0, используем стандартную цену
    if price == 0:
        price = data.get("default_price", 0)
    
    await state.update_data(price=price)
    
    text = f"""
💰 Цена: <b>{price:,.0f}₽</b>

Выбери период оплаты:
"""
    
    await message.answer(text, reply_markup=get_billing_cycle_keyboard())
    await state.set_state(AddSubscription.choosing_cycle)

@router.callback_query(F.data.startswith("cycle:"), AddSubscription.choosing_cycle)
async def choose_cycle(callback: CallbackQuery, state: FSMContext):
    """Выбор периода оплаты"""
    cycle = callback.data.split(":")[1]
    
    cycle_enum = {
        "weekly": BillingCycle.WEEKLY,
        "monthly": BillingCycle.MONTHLY,
        "quarterly": BillingCycle.QUARTERLY,
        "yearly": BillingCycle.YEARLY,
    }.get(cycle, BillingCycle.MONTHLY)
    
    await state.update_data(billing_cycle=cycle_enum)
    
    text = """
📅 <b>Дата начала подписки</b>

Введи дату в формате ДД.ММ.ГГГГ
Или нажми кнопку для выбора:
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="date:today"),
            InlineKeyboardButton(text="📅 Вчера", callback_data="date:yesterday")
        ],
        [
            InlineKeyboardButton(text="📅 Неделю назад", callback_data="date:week_ago"),
            InlineKeyboardButton(text="📅 Месяц назад", callback_data="date:month_ago")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="add_subscription")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(AddSubscription.entering_start_date)
    await callback.answer()

@router.callback_query(F.data.startswith("date:"), AddSubscription.entering_start_date)
async def quick_date_select(callback: CallbackQuery, state: FSMContext):
    """Быстрый выбор даты"""
    date_type = callback.data.split(":")[1]
    
    today = date.today()
    if date_type == "today":
        selected_date = today
    elif date_type == "yesterday":
        selected_date = today - timedelta(days=1)
    elif date_type == "week_ago":
        selected_date = today - timedelta(weeks=1)
    elif date_type == "month_ago":
        selected_date = today - timedelta(days=30)
    else:
        selected_date = today
    
    await state.update_data(start_date=selected_date)
    await finish_add_subscription(callback, state)

@router.message(AddSubscription.entering_start_date)
async def enter_start_date(message: Message, state: FSMContext):
    """Ввод даты начала вручную"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    try:
        # Парсим дату
        parsed_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Введи дату как ДД.ММ.ГГГГ (например, 15.01.2024)")
        return
    
    await state.update_data(start_date=parsed_date)
    
    # Спрашиваем про триал
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏱️ Да, это триал", callback_data="is_trial:yes"),
            InlineKeyboardButton(text="💳 Нет, обычная", callback_data="is_trial:no")
        ]
    ])
    
    await message.answer(
        "Это пробный период (триал)?",
        reply_markup=keyboard
    )
    await state.set_state(AddSubscription.entering_trial_end)

@router.callback_query(F.data.startswith("is_trial:"))
async def handle_trial_question(callback: CallbackQuery, state: FSMContext):
    """Обработка вопроса о триале"""
    is_trial = callback.data.split(":")[1] == "yes"
    await state.update_data(is_trial=is_trial)
    
    if is_trial:
        text = """
⏱️ <b>Когда заканчивается триал?</b>

Введи дату окончания в формате ДД.ММ.ГГГГ:
"""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="3 дня", callback_data="trial_end:3"),
                InlineKeyboardButton(text="7 дней", callback_data="trial_end:7"),
                InlineKeyboardButton(text="14 дней", callback_data="trial_end:14"),
            ],
            [
                InlineKeyboardButton(text="30 дней", callback_data="trial_end:30"),
            ]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await finish_add_subscription(callback, state)

@router.callback_query(F.data.startswith("trial_end:"))
async def quick_trial_end(callback: CallbackQuery, state: FSMContext):
    """Быстрый выбор окончания триала"""
    days = int(callback.data.split(":")[1])
    trial_end = date.today() + timedelta(days=days)
    
    await state.update_data(trial_end_date=trial_end)
    await finish_add_subscription(callback, state)

async def finish_add_subscription(callback: CallbackQuery, state: FSMContext):
    """Завершение добавления подписки"""
    data = await state.get_data()
    
    # Создаём подписку
    subscription = await add_subscription(
        telegram_id=callback.from_user.id,
        name=data.get("name", "Подписка"),
        price=data.get("price", 0),
        billing_cycle=data.get("billing_cycle", BillingCycle.MONTHLY),
        start_date=data.get("start_date", date.today()),
        service_id=data.get("service_id"),
        icon=data.get("icon"),
        color=data.get("color"),
        category=data.get("category"),
        is_trial=data.get("is_trial", False),
        trial_end_date=data.get("trial_end_date"),
        included_services=data.get("included_services", [])
    )
    
    # Формируем сообщение
    cycle_text = {
        BillingCycle.WEEKLY: "в неделю",
        BillingCycle.MONTHLY: "в месяц",
        BillingCycle.QUARTERLY: "в квартал",
        BillingCycle.YEARLY: "в год",
    }.get(data.get("billing_cycle"), "")
    
    text = f"""
✅ <b>Подписка добавлена!</b>

{data.get('icon', '📦')} <b>{data.get('name')}</b>
💰 {data.get('price'):,.0f}₽ {cycle_text}
"""
    
    if data.get("is_trial") and data.get("trial_end_date"):
        days_left = (data["trial_end_date"] - date.today()).days
        text += f"⏱️ Триал до {data['trial_end_date'].strftime('%d.%m.%Y')} ({days_left} дн.)\n"
        text += "\n⚠️ Я напомню тебе отменить до списания!"
    
    if data.get("included_services"):
        text += "\n💡 <i>Совет: эта подписка включает другие сервисы. Проверь дубликаты!</i>"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await state.clear()
    await callback.answer("Подписка добавлена! ✅")

# ============ СВОЯ ПОДПИСКА ============

@router.callback_query(F.data == "custom_subscription")
async def start_custom_subscription(callback: CallbackQuery, state: FSMContext):
    """Добавление своей подписки"""
    await state.set_state(CustomSubscription.entering_name)
    
    text = """
✏️ <b>Своя подписка</b>

Введи название подписки:
"""
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("add_subscription"))
    await callback.message.answer("Название:", reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(CustomSubscription.entering_name)
async def custom_enter_name(message: Message, state: FSMContext):
    """Ввод названия своей подписки"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    await state.update_data(name=message.text.strip(), icon="📦")
    await message.answer("Введи цену подписки (в рублях):")
    await state.set_state(CustomSubscription.entering_price)

@router.message(CustomSubscription.entering_price)
async def custom_enter_price(message: Message, state: FSMContext):
    """Ввод цены своей подписки"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    try:
        price = float(message.text.replace(",", ".").replace("₽", "").strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи корректную цену")
        return
    
    await state.update_data(price=price)
    await message.answer("Выбери период оплаты:", reply_markup=get_billing_cycle_keyboard())
    await state.set_state(CustomSubscription.choosing_cycle)

@router.callback_query(F.data.startswith("cycle:"), CustomSubscription.choosing_cycle)
async def custom_choose_cycle(callback: CallbackQuery, state: FSMContext):
    """Выбор периода для своей подписки"""
    cycle = callback.data.split(":")[1]
    
    cycle_enum = {
        "weekly": BillingCycle.WEEKLY,
        "monthly": BillingCycle.MONTHLY,
        "quarterly": BillingCycle.QUARTERLY,
        "yearly": BillingCycle.YEARLY,
    }.get(cycle, BillingCycle.MONTHLY)
    
    await state.update_data(billing_cycle=cycle_enum)
    
    # Выбор категории
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in SUBSCRIPTION_CATEGORIES.items():
        builder.row(InlineKeyboardButton(text=cat_name, callback_data=f"custom_cat:{cat_id}"))
    
    await callback.message.edit_text(
        "Выбери категорию:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(CustomSubscription.choosing_category)
    await callback.answer()

@router.callback_query(F.data.startswith("custom_cat:"), CustomSubscription.choosing_category)
async def custom_choose_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для своей подписки"""
    category = callback.data.split(":")[1]
    await state.update_data(category=category, start_date=date.today())
    
    # Завершаем добавление
    await finish_add_subscription(callback, state)

# ============ ПОИСК ============

@router.callback_query(F.data == "search_subscription")
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска"""
    await state.set_state(SearchSubscription.entering_query)
    
    text = """
🔍 <b>Поиск подписки</b>

Введи название сервиса:
"""
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("add_subscription"))
    await callback.answer()

@router.message(SearchSubscription.entering_query)
async def process_search(message: Message, state: FSMContext):
    """Обработка поиска"""
    query = message.text.strip()
    results = search_subscriptions(query)
    
    if not results:
        await message.answer(
            f"❌ По запросу «{query}» ничего не найдено.\n\nПопробуй другой запрос или добавь свою подписку.",
            reply_markup=get_categories_keyboard()
        )
        await state.clear()
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    for service in results[:10]:
        builder.row(
            InlineKeyboardButton(
                text=f"{service['icon']} {service['name']} — {service['default_price']}₽",
                callback_data=f"service:{service['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="add_subscription"))
    
    await message.answer(
        f"🔍 Найдено по запросу «{query}»:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AddSubscription.choosing_service)

# ============ РЕДАКТИРОВАНИЕ ============

@router.callback_query(F.data.startswith("edit_sub:"))
async def start_edit(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования"""
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    await state.update_data(editing_sub_id=sub_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Название", callback_data="edit_field:name"),
            InlineKeyboardButton(text="💰 Цена", callback_data="edit_field:price")
        ],
        [
            InlineKeyboardButton(text="📅 Период", callback_data="edit_field:cycle"),
            InlineKeyboardButton(text="📆 След. списание", callback_data="edit_field:next_date")
        ],
        [
            InlineKeyboardButton(text="📝 Заметка", callback_data="edit_field:notes")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"view_sub:{sub_id}")
        ]
    ])
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование: {subscription.name}</b>\n\nЧто изменить?",
        reply_markup=keyboard
    )
    await state.set_state(EditSubscription.choosing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_field:"), EditSubscription.choosing_field)
async def choose_edit_field(callback: CallbackQuery, state: FSMContext):
    """Выбор поля для редактирования"""
    field = callback.data.split(":")[1]
    await state.update_data(editing_field=field)
    
    prompts = {
        "name": "Введи новое название:",
        "price": "Введи новую цену:",
        "notes": "Введи заметку (или 'нет' для удаления):",
        "next_date": "Введи дату следующего списания (ДД.ММ.ГГГГ):"
    }
    
    if field == "cycle":
        await callback.message.edit_text(
            "Выбери новый период оплаты:",
            reply_markup=get_billing_cycle_keyboard()
        )
    else:
        await callback.message.edit_text(prompts.get(field, "Введи новое значение:"))
        await callback.message.answer(prompts.get(field, "Введи:"), reply_markup=get_cancel_keyboard())
    
    await state.set_state(EditSubscription.entering_value)
    await callback.answer()

@router.message(EditSubscription.entering_value)
async def process_edit_value(message: Message, state: FSMContext):
    """Обработка нового значения"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_reply_keyboard())
        return
    
    data = await state.get_data()
    sub_id = data.get("editing_sub_id")
    field = data.get("editing_field")
    
    update_data = {}
    
    if field == "name":
        update_data["name"] = message.text.strip()
    elif field == "price":
        try:
            update_data["price"] = float(message.text.replace(",", ".").replace("₽", "").strip())
        except ValueError:
            await message.answer("❌ Неверная цена")
            return
    elif field == "notes":
        update_data["notes"] = None if message.text.lower() == "нет" else message.text.strip()
    elif field == "next_date":
        try:
            update_data["next_billing_date"] = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Неверный формат даты")
            return
    
    await update_subscription(sub_id, **update_data)
    await state.clear()
    
    await message.answer(
        "✅ Подписка обновлена!",
        reply_markup=get_main_reply_keyboard()
    )

@router.callback_query(F.data.startswith("cycle:"), EditSubscription.entering_value)
async def edit_cycle(callback: CallbackQuery, state: FSMContext):
    """Изменение периода оплаты"""
    data = await state.get_data()
    sub_id = data.get("editing_sub_id")
    cycle = callback.data.split(":")[1]
    
    cycle_enum = {
        "weekly": BillingCycle.WEEKLY,
        "monthly": BillingCycle.MONTHLY,
        "quarterly": BillingCycle.QUARTERLY,
        "yearly": BillingCycle.YEARLY,
    }.get(cycle, BillingCycle.MONTHLY)
    
    await update_subscription(sub_id, billing_cycle=cycle_enum)
    await state.clear()
    
    await callback.message.edit_text("✅ Период оплаты обновлён!", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# ============ ПАУЗА И УДАЛЕНИЕ ============

@router.callback_query(F.data.startswith("pause_sub:"))
async def pause_subscription(callback: CallbackQuery):
    """Пауза/возобновление подписки"""
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    if subscription.status == SubscriptionStatus.PAUSED:
        await update_subscription(sub_id, status=SubscriptionStatus.ACTIVE)
        await callback.answer("▶️ Подписка возобновлена")
    else:
        await update_subscription(sub_id, status=SubscriptionStatus.PAUSED)
        await callback.answer("⏸️ Подписка на паузе")
    
    # Обновляем отображение
    subscription = await get_subscription(sub_id)
    # Перерисовываем детали
    await view_subscription(callback)

@router.callback_query(F.data.startswith("delete_sub:"))
async def confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления"""
    sub_id = int(callback.data.split(":")[1])
    subscription = await get_subscription(sub_id)
    
    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    
    text = f"""
🗑️ <b>Удалить подписку?</b>

{subscription.icon or '📦'} {subscription.name}
💰 {subscription.price:,.0f}₽

Это действие нельзя отменить.
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_keyboard("delete", sub_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete:"))
async def process_delete(callback: CallbackQuery):
    """Удаление подписки"""
    sub_id = int(callback.data.split(":")[1])
    
    subscription = await get_subscription(sub_id)
    name = subscription.name if subscription else "Подписка"
    
    await delete_subscription(sub_id)
    
    await callback.message.edit_text(
        f"🗑️ <b>{name}</b> удалена",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer("Удалено")

@router.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete(callback: CallbackQuery):
    """Отмена удаления"""
    sub_id = int(callback.data.split(":")[1])
    
    # Возвращаемся к просмотру
    callback.data = f"view_sub:{sub_id}"
    await view_subscription(callback)

# ============ ТРИАЛЫ ============

@router.callback_query(F.data == "trials")
async def show_trials(callback: CallbackQuery):
    """Показать триалы"""
    trials = await get_expiring_trials(callback.from_user.id, days=30)
    
    if not trials:
        text = """
⏱️ <b>Пробные периоды</b>

У тебя нет активных триалов.

Добавь подписку с пробным периодом, и я напомню отменить до списания!
"""
    else:
        text = "⏱️ <b>Пробные периоды</b>\n\n"
        for trial in trials:
            days_left = (trial.trial_end_date - date.today()).days
            emoji = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"
            text += f"{emoji} <b>{trial.name}</b>\n"
            text += f"   Осталось: {days_left} дн. (до {trial.trial_end_date.strftime('%d.%m')})\n"
            text += f"   После триала: {trial.price:,.0f}₽\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_trials_keyboard(trials) if trials else get_back_keyboard("add_subscription")
    )
    await callback.answer()

@router.callback_query(F.data == "add_trial")
async def add_trial(callback: CallbackQuery, state: FSMContext):
    """Добавить триал"""
    await state.update_data(is_trial=True)
    await start_add_subscription(callback, state)