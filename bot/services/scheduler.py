"""
⏰ Планировщик уведомлений
"""

from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
import logging

from ..database import async_session, get_upcoming_billings, get_expiring_trials
from ..models import User, Reminder
from ..services.trial_tracker import get_critical_trials
from ..services.report_generator import generate_monthly_text_report
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Настройка планировщика"""
    
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Ежедневная проверка уведомлений в 10:00
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=10, minute=0),
        args=[bot],
        id="daily_reminders",
        replace_existing=True
    )
    
    # Проверка критических триалов в 9:00 и 18:00
    scheduler.add_job(
        send_trial_alerts,
        CronTrigger(hour=9, minute=0),
        args=[bot],
        id="trial_alerts_morning",
        replace_existing=True
    )
    
    scheduler.add_job(
        send_trial_alerts,
        CronTrigger(hour=18, minute=0),
        args=[bot],
        id="trial_alerts_evening",
        replace_existing=True
    )
    
    # Месячные отчёты — 1 числа в 12:00
    scheduler.add_job(
        send_monthly_reports,
        CronTrigger(day=1, hour=12, minute=0),
        args=[bot],
        id="monthly_reports",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Планировщик запущен")
    
    return scheduler


async def send_daily_reminders(bot: Bot):
    """Отправка ежедневных напоминаний о списаниях"""
    
    logger.info("Запуск ежедневных напоминаний...")
    
    async with async_session() as session:
        # Получаем всех пользователей
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            try:
                # Получаем ближайшие списания
                upcoming = await get_upcoming_billings(
                    user.telegram_id, 
                    days=user.notify_before_days
                )
                
                if not upcoming:
                    continue
                
                text = "🔔 <b>Напоминание о списаниях</b>\n\n"
                
                for sub in upcoming:
                    days = (sub.next_billing_date - date.today()).days
                    
                    if days == 0:
                        text += f"⚠️ <b>Сегодня</b>: {sub.name} — {sub.price:,.0f}₽\n"
                    elif days == 1:
                        text += f"🟡 <b>Завтра</b>: {sub.name} — {sub.price:,.0f}₽\n"
                    else:
                        text += f"🟢 <b>Через {days} дн.</b>: {sub.name} — {sub.price:,.0f}₽\n"
                
                total = sum(s.price for s in upcoming)
                text += f"\n💰 Итого: <b>{total:,.0f}₽</b>"
                
                await bot.send_message(user.telegram_id, text)
                logger.info(f"Напоминание отправлено пользователю {user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания {user.telegram_id}: {e}")


async def send_trial_alerts(bot: Bot):
    """Отправка критических уведомлений о триалах"""
    
    logger.info("Проверка критических триалов...")
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            try:
                alerts = await get_critical_trials(user.telegram_id)
                
                if not alerts:
                    continue
                
                text = "⚠️ <b>Триалы заканчиваются!</b>\n\n"
                
                for alert in alerts:
                    if alert.days_left <= 0:
                        text += f"🔴 <b>{alert.subscription.name}</b> — триал закончился!\n"
                    elif alert.days_left == 1:
                        text += f"🔴 <b>{alert.subscription.name}</b> — ЗАВТРА списание {alert.price_after_trial:,.0f}₽!\n"
                    else:
                        text += f"🟡 <b>{alert.subscription.name}</b> — {alert.days_left} дн. до списания {alert.price_after_trial:,.0f}₽\n"
                
                text += "\n💡 Не забудь отменить, если не планируешь продлевать!"
                
                await bot.send_message(user.telegram_id, text)
                logger.info(f"Триал-алерт отправлен {user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки триал-алерта {user.telegram_id}: {e}")


async def send_monthly_reports(bot: Bot):
    """Отправка месячных отчётов"""
    
    logger.info("Отправка месячных отчётов...")
    
    async with async_session() as session:
        # Только пользователи с включёнными отчётами
        result = await session.execute(
            select(User).where(User.notify_monthly_report == True)
        )
        users = result.scalars().all()
        
        for user in users:
            try:
                report = await generate_monthly_text_report(user.telegram_id)
                
                intro = "📊 <b>Твой месячный отчёт готов!</b>\n\n"
                
                await bot.send_message(
                    user.telegram_id,
                    intro + report
                )
                logger.info(f"Месячный отчёт отправлен {user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки отчёта {user.telegram_id}: {e}")


async def send_custom_reminder(bot: Bot, reminder: Reminder):
    """Отправка кастомного напоминания"""
    
    # Получаем подписку
    from ..database import get_subscription
    
    subscription = await get_subscription(reminder.subscription_id)
    if not subscription:
        return
    
    # Получаем пользователя
    async with async_session() as session:
        from ..models import User as UserModel
        result = await session.execute(
            select(UserModel).where(UserModel.id == subscription.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return
        
        text = f"""
🔔 <b>Напоминание</b>

{subscription.icon or '📦'} <b>{subscription.name}</b>

{reminder.message or f'Скоро списание: {subscription.price:,.0f}₽'}

📅 Дата списания: {subscription.next_billing_date.strftime('%d.%m.%Y') if subscription.next_billing_date else 'не указана'}
"""
        
        try:
            await bot.send_message(user.telegram_id, text)
            
            # Отмечаем как отправленное
            reminder.is_sent = True
            reminder.sent_at = datetime.utcnow()
            await session.commit()
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")