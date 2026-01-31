"""
💳 Сервис оплаты через ЮKassa
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

from yookassa import Configuration, Payment
from yookassa.domain.response import PaymentResponse
from yookassa.domain.notification import WebhookNotificationEventType, WebhookNotificationFactory

from ..config import config
from ..database import async_session, update_user_premium
from ..models import Payment as PaymentModel, User, PremiumType
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Настройка ЮKassa
if config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY:
    Configuration.account_id = config.YOOKASSA_SHOP_ID
    Configuration.secret_key = config.YOOKASSA_SECRET_KEY


class PaymentType(Enum):
    """Типы платежей"""
    PREMIUM_MONTHLY = "premium_monthly"
    PREMIUM_YEARLY = "premium_yearly"
    PREMIUM_LIFETIME = "premium_lifetime"


@dataclass
class PaymentInfo:
    """Информация о платеже"""
    payment_id: str
    confirmation_url: str
    amount: float
    description: str


def get_payment_details(payment_type: PaymentType) -> Dict[str, Any]:
    """Получить детали платежа по типу"""
    
    details = {
        PaymentType.PREMIUM_MONTHLY: {
            "amount": config.PREMIUM_MONTHLY_PRICE,
            "description": "SubsManager Premium — 1 месяц",
            "premium_type": PremiumType.MONTHLY,
            "duration_days": 30
        },
        PaymentType.PREMIUM_YEARLY: {
            "amount": config.PREMIUM_YEARLY_PRICE,
            "description": "SubsManager Premium — 1 год",
            "premium_type": PremiumType.YEARLY,
            "duration_days": 365
        },
        PaymentType.PREMIUM_LIFETIME: {
            "amount": config.LIFETIME_PRICE,
            "description": "SubsManager Premium — Навсегда",
            "premium_type": PremiumType.LIFETIME,
            "duration_days": None  # Бессрочно
        }
    }
    
    return details.get(payment_type)


async def create_payment(
    telegram_id: int,
    payment_type: PaymentType,
    return_url: str = None
) -> Optional[PaymentInfo]:
    """
    Создание платежа в ЮKassa
    """
    
    if not config.YOOKASSA_SHOP_ID or not config.YOOKASSA_SECRET_KEY:
        logger.error("ЮKassa не настроена")
        return None
    
    details = get_payment_details(payment_type)
    if not details:
        logger.error(f"Неизвестный тип платежа: {payment_type}")
        return None
    
    # Генерируем уникальный ключ идемпотентности
    idempotence_key = str(uuid.uuid4())
    
    # Формируем return_url
    if not return_url:
        return_url = f"https://t.me/{config.BOT_USERNAME}?start=payment_success"
    
    try:
        # Создаём платёж
        payment = Payment.create({
            "amount": {
                "value": str(details["amount"]),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,  # Автоматическое подтверждение
            "description": details["description"],
            "metadata": {
                "telegram_id": str(telegram_id),
                "payment_type": payment_type.value
            }
        }, idempotence_key)
        
        # Сохраняем в базу
        await save_payment_to_db(
            telegram_id=telegram_id,
            yookassa_payment_id=payment.id,
            amount=details["amount"],
            payment_type=payment_type.value
        )
        
        logger.info(f"Создан платёж {payment.id} для пользователя {telegram_id}")
        
        return PaymentInfo(
            payment_id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
            amount=details["amount"],
            description=details["description"]
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        return None


async def save_payment_to_db(
    telegram_id: int,
    yookassa_payment_id: str,
    amount: float,
    payment_type: str
):
    """Сохранение платежа в базу данных"""
    
    async with async_session() as session:
        # Находим пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return
        
        # Создаём запись о платеже
        payment = PaymentModel(
            user_id=user.id,
            yookassa_payment_id=yookassa_payment_id,
            amount=amount,
            payment_type=payment_type,
            status="pending"
        )
        
        session.add(payment)
        await session.commit()


async def check_payment_status(payment_id: str) -> Optional[str]:
    """Проверка статуса платежа"""
    
    try:
        payment = Payment.find_one(payment_id)
        return payment.status
    except Exception as e:
        logger.error(f"Ошибка проверки платежа {payment_id}: {e}")
        return None


async def process_successful_payment(
    yookassa_payment_id: str,
    telegram_id: int,
    payment_type: str
):
    """Обработка успешного платежа"""
    
    async with async_session() as session:
        # Обновляем статус платежа
        result = await session.execute(
            select(PaymentModel).where(
                PaymentModel.yookassa_payment_id == yookassa_payment_id
            )
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = "succeeded"
            payment.completed_at = datetime.utcnow()
            await session.commit()
        
        # Определяем тип премиума и срок
        payment_type_enum = PaymentType(payment_type)
        details = get_payment_details(payment_type_enum)
        
        if not details:
            logger.error(f"Неизвестный тип платежа: {payment_type}")
            return
        
        premium_type = details["premium_type"]
        duration_days = details["duration_days"]
        
        # Рассчитываем дату окончания
        if duration_days:
            # Проверяем, есть ли уже активный премиум
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.premium_expires and user.premium_expires > datetime.utcnow():
                # Продлеваем от текущей даты окончания
                expires = user.premium_expires + timedelta(days=duration_days)
            else:
                # Новая подписка
                expires = datetime.utcnow() + timedelta(days=duration_days)
        else:
            # Lifetime
            expires = None
        
        # Обновляем премиум статус
        await update_user_premium(telegram_id, premium_type, expires)
        
        logger.info(f"Премиум активирован для {telegram_id}: {premium_type.value}")


async def process_webhook_notification(notification_data: dict) -> bool:
    """
    Обработка webhook-уведомления от ЮKassa
    """
    
    try:
        notification = WebhookNotificationFactory().create(notification_data)
        
        if notification.event == WebhookNotificationEventType.PAYMENT_SUCCEEDED:
            payment = notification.object
            
            # Получаем данные из metadata
            telegram_id = int(payment.metadata.get("telegram_id", 0))
            payment_type = payment.metadata.get("payment_type", "")
            
            if telegram_id and payment_type:
                await process_successful_payment(
                    yookassa_payment_id=payment.id,
                    telegram_id=telegram_id,
                    payment_type=payment_type
                )
                return True
        
        elif notification.event == WebhookNotificationEventType.PAYMENT_CANCELED:
            payment = notification.object
            
            # Обновляем статус в базе
            async with async_session() as session:
                result = await session.execute(
                    select(PaymentModel).where(
                        PaymentModel.yookassa_payment_id == payment.id
                    )
                )
                db_payment = result.scalar_one_or_none()
                
                if db_payment:
                    db_payment.status = "cancelled"
                    await session.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return False


async def get_user_payments(telegram_id: int) -> list:
    """Получить историю платежей пользователя"""
    
    async with async_session() as session:
        # Находим пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return []
        
        # Получаем платежи
        payments_result = await session.execute(
            select(PaymentModel)
            .where(PaymentModel.user_id == user.id)
            .order_by(PaymentModel.created_at.desc())
        )
        
        return payments_result.scalars().all()


def format_payment_type(payment_type: str) -> str:
    """Форматирование типа платежа"""
    
    types = {
        "premium_monthly": "Премиум (месяц)",
        "premium_yearly": "Премиум (год)",
        "premium_lifetime": "Премиум (навсегда)"
    }
    
    return types.get(payment_type, payment_type)


def format_payment_status(status: str) -> str:
    """Форматирование статуса платежа"""
    
    statuses = {
        "pending": "⏳ Ожидает",
        "succeeded": "✅ Успешно",
        "cancelled": "❌ Отменён",
        "waiting_for_capture": "⏳ Обработка"
    }
    
    return statuses.get(status, status)