"""
API эндпоинты для Mini App
Адаптировано под вашу структуру БД
"""
from aiohttp import web
import logging
from datetime import datetime, date, timedelta
from typing import Optional
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Модуль базы данных
db = None

def set_database(database_module):
    """Устанавливает модуль базы данных"""
    global db
    db = database_module
    logger.info("✅ Database module connected to API")

# Путь к статическим файлам
STATIC_DIR = Path(__file__).parent / 'static'


# ========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ========================================

def subscription_to_dict(sub) -> dict:
    """Конвертирует объект Subscription в словарь для API"""
    # Определяем иконку по названию если нет в БД
    icon = getattr(sub, 'icon', None) or get_icon_for_service(sub.name)
    category = getattr(sub, 'category', None) or get_category_for_service(sub.name)
    color = getattr(sub, 'color', None) or get_color_for_service(sub.name)
    
    # Форматируем дату
    next_payment = None
    if sub.next_billing_date:
        if isinstance(sub.next_billing_date, date):
            next_payment = datetime.combine(sub.next_billing_date, datetime.min.time()).isoformat()
        else:
            next_payment = sub.next_billing_date.isoformat()
    
    # Получаем billing_cycle как строку
    billing_cycle = 'monthly'
    if hasattr(sub, 'billing_cycle') and sub.billing_cycle:
        billing_cycle = sub.billing_cycle.value if hasattr(sub.billing_cycle, 'value') else str(sub.billing_cycle)
    
    return {
        'id': sub.id,
        'name': sub.name,
        'price': float(sub.price),
        'currency': getattr(sub, 'currency', 'RUB'),
        'billingCycle': billing_cycle,
        'nextPayment': next_payment,
        'icon': icon,
        'category': category,
        'color': color,
        'notifyDays': getattr(sub, 'notify_days', 3),
        'status': sub.status.value if hasattr(sub.status, 'value') else str(sub.status)
    }


def get_icon_for_service(name: str) -> str:
    """Возвращает иконку для сервиса по названию"""
    name_lower = name.lower()
    icons = {
        'яндекс': '🎵', 'yandex': '🎵',
        'кинопоиск': '🎬', 'kinopoisk': '🎬',
        'spotify': '🎧',
        'youtube': '▶️', 'ютуб': '▶️',
        'netflix': '🎬',
        'vk': '🎵', 'вк': '🎵',
        'okko': '🎥', 'окко': '🎥',
        'ivi': '📺', 'иви': '📺',
        'apple': '🍎',
        'telegram': '✈️', 'телеграм': '✈️',
        'wink': '📱', 'винк': '📱',
        'start': '🎬', 'старт': '🎬',
        'мтс': '📦', 'mts': '📦',
        'сбер': '💚', 'sber': '💚',
        'icloud': '☁️', 'айклауд': '☁️',
        'google': '🔵', 'гугл': '🔵',
        'dropbox': '📦',
        'notion': '📝',
        'figma': '🎨',
        'chatgpt': '🤖', 'openai': '🤖',
        'github': '💻',
        'linkedin': '💼',
        'twitch': '🎮',
        'discord': '🎮',
        'zoom': '📹',
        'microsoft': '🪟',
        'adobe': '🎨',
        'canva': '🎨',
    }
    
    for key, icon in icons.items():
        if key in name_lower:
            return icon
    
    return '💳'


def get_category_for_service(name: str) -> str:
    """Возвращает категорию для сервиса"""
    name_lower = name.lower()
    
    music = ['spotify', 'яндекс музыка', 'vk музыка', 'apple music', 'звук', 'deezer', 'tidal']
    video = ['netflix', 'кинопоиск', 'okko', 'ivi', 'wink', 'start', 'premier', 'hbo', 'disney', 'amediateka', 'youtube']
    bundles = ['яндекс плюс', 'яндекс+', 'сберпрайм', 'мтс premium', 'tinkoff pro']
    messengers = ['telegram', 'discord', 'slack', 'whatsapp']
    storage = ['icloud', 'google one', 'dropbox', 'onedrive', 'яндекс диск', 'облако']
    productivity = ['notion', 'evernote', 'todoist', 'trello']
    design = ['figma', 'canva', 'adobe', 'photoshop']
    dev = ['github', 'gitlab', 'jetbrains', 'chatgpt', 'copilot']
    
    for service in music:
        if service in name_lower:
            return 'Музыка'
    for service in video:
        if service in name_lower:
            return 'Видео'
    for service in bundles:
        if service in name_lower:
            return 'Бандл'
    for service in messengers:
        if service in name_lower:
            return 'Мессенджеры'
    for service in storage:
        if service in name_lower:
            return 'Хранилище'
    for service in productivity:
        if service in name_lower:
            return 'Продуктивность'
    for service in design:
        if service in name_lower:
            return 'Дизайн'
    for service in dev:
        if service in name_lower:
            return 'Разработка'
    
    return 'Другое'


def get_color_for_service(name: str) -> str:
    """Возвращает цвет для сервиса"""
    name_lower = name.lower()
    colors = {
        'яндекс': '#FF0000',
        'кинопоиск': '#FF6B00',
        'spotify': '#1DB954',
        'youtube': '#FF0000',
        'netflix': '#E50914',
        'vk': '#0077FF',
        'okko': '#6B4EE6',
        'ivi': '#EA1E63',
        'apple': '#FC3C44',
        'telegram': '#0088CC',
        'wink': '#7C3AED',
        'мтс': '#E30611',
        'сбер': '#21A038',
        'tinkoff': '#FFDD2D',
        'google': '#4285F4',
        'icloud': '#007AFF',
        'notion': '#000000',
        'figma': '#F24E1E',
        'github': '#333333',
        'discord': '#5865F2',
        'twitch': '#9146FF',
    }
    
    for key, color in colors.items():
        if key in name_lower:
            return color
    
    return '#6366f1'


def find_duplicates(subscriptions: list) -> list:
    """Находит дубликаты/пересечения подписок"""
    duplicates = []
    names = [s.get('name', '').lower() if isinstance(s, dict) else s.name.lower() for s in subscriptions]
    
    def get_name(s):
        return s.get('name', '') if isinstance(s, dict) else s.name
    
    def get_price(s):
        return s.get('price', 0) if isinstance(s, dict) else s.price
    
    # Яндекс Плюс включает многое
    has_yandex_plus = any('яндекс плюс' in n or 'яндекс+' in n or 'yandex plus' in n for n in names)
    
    if has_yandex_plus:
        for sub in subscriptions:
            name = get_name(sub).lower()
            if 'кинопоиск' in name and 'яндекс' not in name:
                duplicates.append({
                    'services': ['Яндекс Плюс', get_name(sub)],
                    'message': 'Кинопоиск уже входит в Яндекс Плюс! Можно сэкономить.',
                    'savings': float(get_price(sub))
                })
            elif 'яндекс музыка' in name:
                duplicates.append({
                    'services': ['Яндекс Плюс', get_name(sub)],
                    'message': 'Яндекс Музыка уже входит в Яндекс Плюс!',
                    'savings': float(get_price(sub))
                })
            elif 'яндекс диск' in name:
                duplicates.append({
                    'services': ['Яндекс Плюс', get_name(sub)],
                    'message': 'Расширенный Яндекс Диск входит в Яндекс Плюс!',
                    'savings': float(get_price(sub))
                })
    
    # СберПрайм
    has_sber = any('сберпрайм' in n or 'сбер прайм' in n or 'sberprime' in n for n in names)
    
    if has_sber:
        for sub in subscriptions:
            name = get_name(sub).lower()
            if 'okko' in name or 'окко' in name:
                duplicates.append({
                    'services': ['СберПрайм', get_name(sub)],
                    'message': 'Okko входит в СберПрайм!',
                    'savings': float(get_price(sub))
                })
            elif 'сберзвук' in name or 'звук' in name:
                duplicates.append({
                    'services': ['СберПрайм', get_name(sub)],
                    'message': 'СберЗвук входит в СберПрайм!',
                    'savings': float(get_price(sub))
                })
    
    # МТС Premium
    has_mts = any('мтс premium' in n or 'mts premium' in n or 'мтс премиум' in n for n in names)
    
    if has_mts:
        for sub in subscriptions:
            name = get_name(sub).lower()
            if 'kion' in name or 'кион' in name:
                duplicates.append({
                    'services': ['МТС Premium', get_name(sub)],
                    'message': 'KION входит в МТС Premium!',
                    'savings': float(get_price(sub))
                })
    
    # Tinkoff Pro
    has_tinkoff = any('tinkoff pro' in n or 'тинькофф про' in n for n in names)
    
    if has_tinkoff:
        for sub in subscriptions:
            name = get_name(sub).lower()
            if 'яндекс плюс' in name:
                duplicates.append({
                    'services': ['Tinkoff Pro', get_name(sub)],
                    'message': 'Яндекс Плюс входит в Tinkoff Pro!',
                    'savings': float(get_price(sub))
                })
    
    return duplicates


# ========================================
# API HANDLERS
# ========================================

async def handle_sync(request):
    """
    POST /api/sync
    Главный эндпоинт синхронизации с Mini App
    """
    try:
        data = await request.json()
        telegram_id = data.get('telegramId')
        user_data = data.get('userData', {})
        
        if not telegram_id:
            return web.json_response({
                'success': False,
                'error': 'telegramId is required'
            }, status=400)
        
        telegram_id = int(telegram_id)
        
        # Получаем или создаём пользователя
        user = await db.get_or_create_user(
            telegram_id=telegram_id,
            username=user_data.get('username'),
            first_name=user_data.get('first_name', 'Пользователь')
        )
        
        # Получаем подписки
        subscriptions_raw = await db.get_user_subscriptions(telegram_id)
        
        # Конвертируем в формат для Mini App
        subscriptions = [subscription_to_dict(sub) for sub in subscriptions_raw]
        
        # Вычисляем статистику
        total_monthly = await db.get_monthly_spending(telegram_id)
        
        # Находим скорые списания
        upcoming = 0
        trials = []
        now = datetime.now()
        today = date.today()
        
        for sub in subscriptions:
            try:
                if sub['nextPayment']:
                    next_date = datetime.fromisoformat(sub['nextPayment'].replace('Z', '+00:00'))
                    days_until = (next_date.date() - today).days
                    
                    if 0 <= days_until <= 7:
                        upcoming += 1
                    
                    if 0 <= days_until <= 3:
                        trials.append({
                            'id': sub['id'],
                            'name': sub['name'],
                            'endsIn': days_until,
                            'price': sub['price'],
                            'action': f"Списание {'сегодня' if days_until == 0 else 'завтра' if days_until == 1 else f'через {days_until} дн.'}"
                        })
            except Exception as e:
                logger.warning(f"Error parsing date for {sub.get('name')}: {e}")
        
        # Проверяем дубликаты
        duplicates = find_duplicates(subscriptions)
        
        # Проверяем премиум статус
        is_premium = await db.is_premium(telegram_id)
        
        return web.json_response({
            'success': True,
            'user': {
                'id': telegram_id,
                'name': user.first_name or user.username or 'Пользователь',
                'username': user.username or '',
                'isPremium': is_premium
            },
            'subscriptions': subscriptions,
            'stats': {
                'totalMonthly': total_monthly,
                'totalYearly': round(total_monthly * 12, 2),
                'activeCount': len(subscriptions),
                'upcomingPayments': upcoming
            },
            'duplicates': duplicates,
            'trials': trials
        })
        
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_get_subscriptions(request):
    """
    GET /api/subscriptions/{telegram_id}
    Получить все подписки пользователя
    """
    try:
        telegram_id = int(request.match_info['telegram_id'])
        subscriptions_raw = await db.get_user_subscriptions(telegram_id)
        subscriptions = [subscription_to_dict(sub) for sub in subscriptions_raw]
        
        return web.json_response({
            'success': True,
            'subscriptions': subscriptions
        })
    except Exception as e:
        logger.error(f"Get subscriptions error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_add_subscription(request):
    """
    POST /api/subscriptions
    Добавить новую подписку
    """
    try:
        data = await request.json()
        telegram_id = int(data.get('telegramId'))
        sub_data = data.get('subscription', {})
        
        # Парсим дату
        next_payment = sub_data.get('nextPayment')
        if next_payment:
            if isinstance(next_payment, str):
                # Пробуем разные форматы
                try:
                    start_date = datetime.fromisoformat(next_payment.replace('Z', '+00:00')).date()
                except:
                    start_date = datetime.strptime(next_payment[:10], '%Y-%m-%d').date()
            else:
                start_date = date.today() + timedelta(days=30)
        else:
            start_date = date.today() + timedelta(days=30)
        
        # Определяем billing_cycle (по умолчанию monthly)
        billing_cycle_str = sub_data.get('billingCycle', 'monthly').lower()
        
        # Импортируем BillingCycle из models
        from .models import BillingCycle
        
        billing_cycle_map = {
            'weekly': BillingCycle.WEEKLY,
            'monthly': BillingCycle.MONTHLY,
            'quarterly': BillingCycle.QUARTERLY,
            'yearly': BillingCycle.YEARLY,
        }
        billing_cycle = billing_cycle_map.get(billing_cycle_str, BillingCycle.MONTHLY)
        
        # Добавляем подписку
        new_sub = await db.add_subscription(
            telegram_id=telegram_id,
            name=sub_data.get('name'),
            price=float(sub_data.get('price', 0)),
            billing_cycle=billing_cycle,
            start_date=start_date,
            # Дополнительные поля если есть в модели
            # icon=sub_data.get('icon'),
            # category=sub_data.get('category'),
            # color=sub_data.get('color'),
        )
        
        return web.json_response({
            'success': True,
            'subscription': subscription_to_dict(new_sub)
        })
    except Exception as e:
        logger.error(f"Add subscription error: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_add_subscription(request):
    """
    POST /api/subscriptions
    Добавить новую подписку
    """
    try:
        data = await request.json()
        telegram_id = int(data.get('telegramId'))
        sub_data = data.get('subscription', {})
        
        # Парсим дату
        next_payment = sub_data.get('nextPayment')
        if next_payment:
            if isinstance(next_payment, str):
                try:
                    start_date = datetime.fromisoformat(next_payment.replace('Z', '+00:00')).date()
                except:
                    try:
                        start_date = datetime.strptime(next_payment[:10], '%Y-%m-%d').date()
                    except:
                        start_date = date.today() + timedelta(days=30)
            else:
                start_date = date.today() + timedelta(days=30)
        else:
            start_date = date.today() + timedelta(days=30)
        
        # Определяем billing_cycle
        billing_cycle_str = sub_data.get('billingCycle', 'monthly').lower()
        
        from .models import BillingCycle
        
        billing_cycle_map = {
            'weekly': BillingCycle.WEEKLY,
            'monthly': BillingCycle.MONTHLY,
            'quarterly': BillingCycle.QUARTERLY,
            'yearly': BillingCycle.YEARLY,
            'lifetime': BillingCycle.LIFETIME,
        }
        billing_cycle = billing_cycle_map.get(billing_cycle_str, BillingCycle.MONTHLY)
        
        # Добавляем подписку со всеми полями
        new_sub = await db.add_subscription(
            telegram_id=telegram_id,
            name=sub_data.get('name'),
            price=float(sub_data.get('price', 0)),
            billing_cycle=billing_cycle,
            start_date=start_date,
            icon=sub_data.get('icon'),
            category=sub_data.get('category'),
            color=sub_data.get('color'),
            currency=sub_data.get('currency', 'RUB'),
        )
        
        return web.json_response({
            'success': True,
            'subscription': subscription_to_dict(new_sub)
        })
    except Exception as e:
        logger.error(f"Add subscription error: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_delete_subscription(request):
    """
    DELETE /api/subscriptions/{id}
    Удалить подписку
    """
    try:
        sub_id = int(request.match_info['id'])
        
        await db.delete_subscription(sub_id)
        
        return web.json_response({'success': True})
    except Exception as e:
        logger.error(f"Delete subscription error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_duplicates(request):
    """
    GET /api/duplicates/{telegram_id}
    Проверить дубликаты подписок
    """
    try:
        telegram_id = int(request.match_info['telegram_id'])
        subscriptions_raw = await db.get_user_subscriptions(telegram_id)
        subscriptions = [subscription_to_dict(sub) for sub in subscriptions_raw]
        
        duplicates = find_duplicates(subscriptions)
        
        return web.json_response({
            'success': True,
            'duplicates': duplicates
        })
    except Exception as e:
        logger.error(f"Duplicates error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_cancel_guide(request):
    """
    GET /api/cancel-guides/{service}
    Получить инструкцию по отмене подписки
    """
    service = request.match_info['service'].lower()
    
    guides = {
        'яндекс плюс': {
            'steps': [
                'Откройте plus.yandex.ru или приложение Яндекс',
                'Нажмите на иконку профиля',
                'Выберите "Управление подпиской"',
                'Нажмите "Отменить подписку"',
                'Подтвердите отмену'
            ],
            'note': 'Подписка будет активна до конца оплаченного периода. Вы потеряете доступ к Кинопоиску, Яндекс Музыке и другим сервисам.'
        },
        'кинопоиск': {
            'steps': [
                'Откройте kinopoisk.ru',
                'Перейдите в профиль → Настройки',
                'Найдите раздел "Подписка"',
                'Нажмите "Отменить"'
            ],
            'note': 'Если подписка через Яндекс Плюс — отменяйте там.'
        },
        'spotify': {
            'steps': [
                'Откройте spotify.com/account',
                'Войдите в аккаунт',
                'Нажмите "Управление подпиской"',
                'Выберите "Отменить Premium"'
            ],
            'note': 'Отмена только через сайт! В приложении нельзя.'
        },
        'youtube premium': {
            'steps': [
                'Откройте youtube.com/paid_memberships',
                'Войдите в аккаунт',
                'Нажмите "Управление"',
                'Выберите "Отменить подписку"'
            ],
            'note': 'Можно приостановить до 6 месяцев вместо отмены.'
        },
        'netflix': {
            'steps': [
                'Откройте netflix.com/account',
                'В разделе "Подписка" нажмите "Отменить"',
                'Подтвердите отмену'
            ],
            'note': 'Доступ сохранится до конца периода. Профили хранятся 10 месяцев.'
        },
        'telegram premium': {
            'steps': [
                'Откройте Telegram → Настройки',
                'Нажмите на "Telegram Premium"',
                'Прокрутите до "Управление подпиской"',
                'Отмените через App Store / Google Play'
            ],
            'note': 'Отмена через магазин приложений, где оформляли.'
        },
        'apple music': {
            'steps': [
                'Откройте Настройки на iPhone',
                'Нажмите на своё имя → Подписки',
                'Выберите Apple Music',
                'Нажмите "Отменить подписку"'
            ],
            'note': 'На Android: Apple Music → Настройки → Управление подпиской.'
        },
        'okko': {
            'steps': [
                'Откройте okko.tv/account',
                'Перейдите в "Подписка"',
                'Нажмите "Отключить автопродление"'
            ],
            'note': 'Если через СберПрайм — отменяйте в приложении СберБанк.'
        },
        'ivi': {
            'steps': [
                'Откройте ivi.ru → Профиль',
                'Перейдите в "Подписка"',
                'Нажмите "Отменить подписку"'
            ],
            'note': 'Доступ сохранится до конца оплаченного периода.'
        },
        'vk музыка': {
            'steps': [
                'Откройте vk.com/settings?act=payments',
                'Найдите раздел "Подписки"',
                'Выберите VK Музыка',
                'Нажмите "Отменить"'
            ],
            'note': 'Также можно через приложение VK в настройках.'
        },
        'сберпрайм': {
            'steps': [
                'Откройте приложение СберБанк',
                'Перейдите в "Прайм" или "Подписки"',
                'Выберите СберПрайм',
                'Нажмите "Отключить"'
            ],
            'note': 'При отключении потеряете Okko, СберЗвук и другие бонусы.'
        },
        'мтс premium': {
            'steps': [
                'Откройте приложение Мой МТС',
                'Перейдите в "Услуги" → "Подписки"',
                'Найдите МТС Premium',
                'Нажмите "Отключить"'
            ],
            'note': 'Также можно через личный кабинет на mts.ru'
        }
    }
    
    guide = guides.get(service, {
        'steps': [
            'Откройте официальный сайт или приложение сервиса',
            'Войдите в свой аккаунт',
            'Найдите раздел "Настройки" или "Профиль"',
            'Перейдите в "Подписка" или "Оплата"',
            'Нажмите "Отменить подписку"'
        ],
        'note': 'Если не получается — обратитесь в поддержку сервиса.'
    })
    
    return web.json_response({
        'success': True,
        'guide': guide
    })


async def handle_create_payment(request):
    """
    POST /api/payments/create
    Создать платёж для поддержки проекта
    """
    try:
        data = await request.json()
        telegram_id = int(data.get('telegramId'))
        amount = data.get('amount', 399)
        
        # Импортируем config для получения username бота
        from .config import config
        bot_username = getattr(config, 'BOT_USERNAME', None)
        
        if not bot_username:
            # Пробуем получить из переменных окружения
            import os
            bot_username = os.getenv('BOT_USERNAME', 'your_bot')
        
        return web.json_response({
            'success': True,
            'paymentUrl': f'https://t.me/{bot_username}?start=donate_{amount}'
        })
    except Exception as e:
        logger.error(f"Create payment error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_analytics(request):
    """
    GET /api/analytics/{telegram_id}
    Получить аналитику по подпискам
    """
    try:
        telegram_id = int(request.match_info['telegram_id'])
        subscriptions_raw = await db.get_user_subscriptions(telegram_id)
        subscriptions = [subscription_to_dict(sub) for sub in subscriptions_raw]
        
        # Группировка по категориям
        by_category = {}
        for sub in subscriptions:
            cat = sub.get('category', 'Другое')
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'count': 0, 'items': []}
            by_category[cat]['total'] += sub.get('price', 0)
            by_category[cat]['count'] += 1
            by_category[cat]['items'].append(sub.get('name'))
        
        total = sum(s.get('price', 0) for s in subscriptions)
        avg = total / len(subscriptions) if subscriptions else 0
        most_expensive = max(subscriptions, key=lambda x: x.get('price', 0)) if subscriptions else None
        
        return web.json_response({
            'success': True,
            'analytics': {
                'byCategory': by_category,
                'totalMonthly': total,
                'totalYearly': total * 12,
                'averagePerSub': round(avg),
                'mostExpensive': most_expensive
            }
        })
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_health(request):
    """GET /health - Health check"""
    return web.json_response({
        'status': 'ok',
        'service': 'SubTrack API',
        'timestamp': datetime.now().isoformat()
    })


# ========================================
# WEB APP SETUP
# ========================================

async def handle_index(request):
    """GET / - Главная страница Mini App"""
    index_path = STATIC_DIR / 'index.html'
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="Mini App not found", status=404)


async def handle_static(request):
    """Отдача статических файлов"""
    filename = request.match_info.get('filename', 'index.html')
    filepath = STATIC_DIR / filename
    if filepath.exists() and filepath.is_file():
        return web.FileResponse(filepath)
    return web.Response(text="Not found", status=404)

def create_app():
    """Создаёт и настраивает веб-приложение"""
    app = web.Application()
    
    # CORS middleware
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Telegram-Init-Data, X-Telegram-Id'
        return response
    
    app.middlewares.append(cors_middleware)
    
    # === Статические файлы и Mini App ===
    app.router.add_get('/', handle_index)
    app.router.add_get('/index.html', handle_index)
    app.router.add_get('/static/{filename}', handle_static)
    
    # === API роуты ===
    app.router.add_route('OPTIONS', '/{path:.*}', lambda r: web.Response())
    app.router.add_get('/health', handle_health)
    app.router.add_post('/api/sync', handle_sync)
    app.router.add_get('/api/subscriptions/{telegram_id}', handle_get_subscriptions)
    app.router.add_post('/api/subscriptions', handle_add_subscription)
    app.router.add_put('/api/subscriptions/{id}', handle_update_subscription)
    app.router.add_delete('/api/subscriptions/{id}', handle_delete_subscription)
    app.router.add_get('/api/duplicates/{telegram_id}', handle_duplicates)
    app.router.add_get('/api/cancel-guides/{service}', handle_cancel_guide)
    app.router.add_post('/api/payments/create', handle_create_payment)
    app.router.add_get('/api/analytics/{telegram_id}', handle_analytics)
    
    return app


async def run_api(host='0.0.0.0', port=8080):
    """Запускает API сервер"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🌐 API server started on http://{host}:{port}")
    return runner
