from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from datetime import datetime, date

from ..services.payment import (
    create_payment, PaymentType, get_payment_details,
    get_user_payments, format_payment_type, format_payment_status,
    check_payment_status, process_successful_payment
)
from ..database import get_user, is_premium
from ..keyboards.inline import get_premium_keyboard, get_back_keyboard, get_main_menu_keyboard
from ..config import config

router = Router()


@router.callback_query(F.data.startswith("buy_premium:"))
async def buy_premium(callback: CallbackQuery):
    """Начало покупки премиума"""
    
    plan = callback.data.split(":")[1]
    
    # Маппинг планов
    plan_map = {
        "monthly": PaymentType.PREMIUM_MONTHLY,
        "yearly": PaymentType.PREMIUM_YEARLY,
        "lifetime": PaymentType.PREMIUM_LIFETIME
    }
    
    payment_type = plan_map.get(plan)
    if not payment_type:
        await callback.answer("Неизвестный план", show_alert=True)
        return
    
    details = get_payment_details(payment_type)
    
    # Проверяем, настроена ли ЮKassa
    if not config.YOOKASSA_SHOP_ID or not config.YOOKASSA_SECRET_KEY:
        text = f"""
💳 <b>Оплата временно недоступна</b>

Мы работаем над подключением платежей.
Пока что бот полностью бесплатен! 🎉

Выбранный план: <b>{details['description']}</b>
Стоимость: <b>{details['amount']}₽</b>

Следи за обновлениями!
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("premium_info"))
        await callback.answer()
        return
    
    # Создаём платёж
    payment_info = await create_payment(
        telegram_id=callback.from_user.id,
        payment_type=payment_type
    )
    
    if not payment_info:
        await callback.answer("Ошибка создания платежа. Попробуй позже.", show_alert=True)
        return
    
    text = f"""
💳 <b>Оплата Premium</b>

📦 <b>Тариф:</b> {details['description']}
💰 <b>Сумма:</b> {details['amount']}₽

Нажми кнопку ниже для перехода к оплате.
После успешной оплаты Premium активируется автоматически.

🔒 Безопасная оплата через ЮKassa
"""
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"💳 Оплатить {details['amount']}₽",
            url=payment_info.confirmation_url
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_payment:{payment_info.payment_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="premium_info")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery):
    """Проверка статуса платежа"""
    
    payment_id = callback.data.split(":")[1]
    
    status = await check_payment_status(payment_id)
    
    if status == "succeeded":
        # Платёж успешен — проверяем, активирован ли премиум
        has_premium = await is_premium(callback.from_user.id)
        
        if has_premium:
            text = """
🎉 <b>Поздравляем!</b>

Оплата прошла успешно! Premium активирован.

✨ <b>Теперь тебе доступно:</b>
• 📋 Безлимит подписок
• 📊 Расширенная аналитика
• 📈 Детальные отчёты и тренды
• 📤 Экспорт данных
• 🔔 Приоритетные уведомления

Спасибо за поддержку проекта! 💜
"""
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
            await callback.answer("Premium активирован! 🎉")
        else:
            # Нужно дообработать (может быть задержка webhook)
            await callback.answer("Платёж обрабатывается. Подожди минуту и проверь снова.", show_alert=True)
    
    elif status == "pending":
        await callback.answer("Платёж ещё не завершён. Заверши оплату и проверь снова.", show_alert=True)
    
    elif status == "canceled":
        text = """
❌ <b>Платёж отменён</b>

Оплата была отменена или не завершена.
Ты можешь попробовать снова.
"""
        await callback.message.edit_text(text, reply_markup=get_premium_keyboard())
        await callback.answer()
    
    else:
        await callback.answer(f"Статус платежа: {status}", show_alert=True)


@router.callback_query(F.data == "payment_history")
async def show_payment_history(callback: CallbackQuery):
    """История платежей"""
    
    payments = await get_user_payments(callback.from_user.id)
    
    if not payments:
        text = """
📜 <b>История платежей</b>

У тебя пока нет платежей.
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("premium_info"))
        await callback.answer()
        return
    
    text = "📜 <b>История платежей</b>\n\n"
    
    for payment in payments[:10]:
        status_text = format_payment_status(payment.status)
        type_text = format_payment_type(payment.payment_type)
        date_text = payment.created_at.strftime("%d.%m.%Y %H:%M")
        
        text += f"{status_text} <b>{type_text}</b>\n"
        text += f"   💰 {payment.amount:,.0f}₽ • {date_text}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("premium_info"))
    await callback.answer()


@router.callback_query(F.data == "cancel_premium")
async def cancel_premium_info(callback: CallbackQuery):
    """Информация об отмене премиума"""
    
    user = await get_user(callback.from_user.id)
    has_premium = await is_premium(callback.from_user.id)
    
    if not has_premium:
        await callback.answer("У тебя нет активной подписки", show_alert=True)
        return
    
    if user.premium_type == PremiumType.LIFETIME:
        text = """
♾️ <b>Пожизненный Premium</b>

У тебя пожизненная подписка — её нельзя отменить, она действует навсегда!

Если возникли проблемы — напиши в поддержку.
"""
    else:
        expires_text = user.premium_expires.strftime("%d.%m.%Y") if user.premium_expires else "Неизвестно"
        
        text = f"""
⚙️ <b>Управление подпиской</b>

📅 Текущий период до: <b>{expires_text}</b>

Автопродление отключено по умолчанию.
Твоя подписка просто закончится в указанную дату.

Если хочешь продлить — выбери план:
"""
    
    builder = InlineKeyboardBuilder()
    
    if user.premium_type != PremiumType.LIFETIME:
        builder.row(
            InlineKeyboardButton(text="📅 Продлить на месяц", callback_data="buy_premium:monthly"),
            InlineKeyboardButton(text="📆 Продлить на год", callback_data="buy_premium:yearly")
        )
    
    builder.row(
        InlineKeyboardButton(text="📜 История платежей", callback_data="payment_history")
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# Обработка команды после успешной оплаты (deep link)
@router.message(F.text.startswith("/start payment_success"))
async def payment_success_deeplink(message: Message):
    """Обработка возврата после успешной оплаты"""
    
    has_premium = await is_premium(message.from_user.id)
    
    if has_premium:
        text = """
🎉 <b>Добро пожаловать в Premium!</b>

Твоя оплата успешно обработана.

✨ <b>Теперь тебе доступно:</b>
• 📋 Безлимит подписок
• 📊 Расширенная аналитика
• 📈 Детальные отчёты
• 📤 Экспорт данных
• 🔔 Приоритетные уведомления

Начинай пользоваться! 👇
"""
    else:
        text = """
⏳ <b>Обработка платежа...</b>

Платёж получен и обрабатывается.
Обычно это занимает несколько секунд.

Нажми кнопку ниже, чтобы проверить статус.
"""
    
    await message.answer(text, reply_markup=get_main_menu_keyboard())