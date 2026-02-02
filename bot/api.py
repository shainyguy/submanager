"""
API эндпоинты для Mini App
"""
from aiohttp import web
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Ссылка на функции базы данных (импортируем позже)
db = None

def set_database(database_module):
    """Устанавливает модуль базы данных"""
    global db
    db = database_module

async def handle_sync(request):
    """
    POST /api/sync
    Синхронизация данных пользователя с Mini App
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
        user = await db.get_user(telegram_id)
        
        if not user:
            # Создаём нового пользователя
            await db.create_user(
                telegram_id=telegram_id,
                username=user_data.get('username', ''),
                first_name=user_data.get('first_name', 'Пользователь')
            )
            user = await db.get_user(telegram_id)
        
        # Получаем подписки
        subscriptions = await db.get_subscriptions(telegram_id)
        
        # Форматируем подписки для Mini App
        formatted_subs = []
        for sub in subscriptions:
            formatted_subs.append({
                'id': sub['id'],
                'name': sub['name'],
                'price': sub['price'],
                'currency': sub.get('currency', 'RUB'),
                'nextPayment': sub.get('next_payment', sub.get('next_date', '')),
                'icon': sub.get('icon', '💳'),
                'category': sub.get('category', 'Другое'),
                'color': sub.get('color', '#6366f1'),
                'notifyDays': sub.get('notify_days', 3)
            })
        
        # Вычисляем статистику
        total_monthly = sum(s['price'] for s in formatted_subs)
        
        # Находим скорые списания
        upcoming = 0
        trials = []
        now = datetime.now()
        
        for sub in formatted_subs:
            try:
                if sub['nextPayment']:
                    next_date = datetime.fromisoformat(sub['nextPayment'].replace('Z', '+00:00'))
                    days_until = (next_date.replace(tzinfo=None) - now).days
                    
                    if 0 <= days_until <= 7:
                        upcoming += 1
                    
                    if 0 <= days_until <= 3:
                        trials.append({
                            'id': sub['id'],
                            'name': sub['name'],
                            'endsIn': days_until,
                            'price': sub['price'],
                            'action': f"Списание {'сегодня' if days_until == 0 else f'через {days_until} дн.'}"
                        })
            except:
                pass
        
        # Проверяем дубликаты
        duplicates = find_duplicates(formatted_subs)
        
        return web.json_response({
            'success': True,
            'user': {
                'id': telegram_id,
                'name': user.get('first_name', user.get('username', 'Пользователь')),
                'username': user.get('username', ''),
                'isPremium': user.get('is_premium', False)
            },
            'subscriptions': formatted_subs,
            'stats': {
                'totalMonthly': total_monthly,
                'totalYearly': total_monthly * 12,
                'activeCount': len(formatted_subs),
                'upcomingPayments': upcoming
            },
            'duplicates': duplicates,
            'trials': trials
        })
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
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
        subscriptions = await db.get_subscriptions(telegram_id)
        
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
        sub = data.get('subscription', {})
        
        # Добавляем подписку в БД
        sub_id = await db.add_subscription(
            telegram_id=telegram_id,
            name=sub.get('name'),
            price=sub.get('price'),
            next_payment=sub.get('nextPayment'),
            icon=sub.get('icon', '💳'),
            category=sub.get('category', 'Другое'),
            color=sub.get('color', '#6366f1'),
            notify_days=sub.get('notifyDays', 3)
        )
        
        return web.json_response({
            'success': True,
            'subscription': {
                'id': sub_id,
                **sub
            }
        })
    except Exception as e:
        logger.error(f"Add subscription error: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def handle_update_subscription(request):
    """
    PUT /api/subscriptions/{id}
    Обновить подписку
    """
    try:
        sub_id = int(request.match_info['id'])
        data = await request.json()
        sub = data.get('subscription', {})
        
        await db.update_subscription(
            sub_id=sub_id,
            name=sub.get('name'),
            price=sub.get('price'),
            next_payment=sub.get('nextPayment'),
            icon=sub.get('icon'),
            category=sub.get('category'),
            color=sub.get('color')
        )
        
        return web.json_response({'success': True})
    except Exception as e:
        logger.error(f"Update subscription error: {e}")
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
        subscriptions = await db.get_subscriptions(telegram_id)
        
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
                'Откройте приложение Яндекс или сайт plus.yandex.ru',
                'Нажмите на иконку профиля в правом верхнем углу',
                'Выберите "Управление подпиской"',
                'Нажмите "Отменить подписку"',
                'Подтвердите отмену'
            ],
            'note': 'Подписка будет активна до конца оплаченного периода. После отмены вы потеряете доступ к Кинопоиску, Яндекс Музыке и другим сервисам.'
        },
        'кинопоиск': {
            'steps': [
                'Откройте kinopoisk.ru или приложение Кинопоиск',
                'Перейдите в настройки профиля',
                'Найдите раздел "Подписка"',
                'Нажмите "Отменить подписку"',
                'Подтвердите отмену'
            ],
            'note': 'Если подписка оформлена через Яндекс Плюс — отменять нужно там. Отдельная подписка Кинопоиск отменяется на сайте.'
        },
        'spotify': {
            'steps': [
                'Откройте spotify.com/account в браузере',
                'Войдите в свой аккаунт',
                'Перейдите в раздел "Управление подпиской"',
                'Нажмите "Изменить или отменить"',
                'Выберите "Отменить Premium"'
            ],
            'note': 'Отмена через мобильное приложение недоступна! Только через сайт. После отмены аккаунт станет бесплатным.'
        },
        'youtube premium': {
            'steps': [
                'Откройте youtube.com/paid_memberships',
                'Войдите в аккаунт Google',
                'Нажмите "Управление подпиской"',
                'Выберите "Отменить подписку"',
                'Укажите причину и подтвердите'
            ],
            'note': 'Можно приостановить подписку на срок до 6 месяцев вместо полной отмены.'
        },
        'netflix': {
            'steps': [
                'Откройте netflix.com/account',
                'Войдите в аккаунт',
                'В разделе "Подписка и оплата" нажмите "Отменить подписку"',
                'Подтвердите отмену'
            ],
            'note': 'Вы сможете смотреть до конца оплаченного периода. Профили и история сохранятся 10 месяцев.'
        },
        'vk музыка': {
            'steps': [
                'Откройте vk.com/settings?act=payments',
                'Найдите раздел "Подписки"',
                'Выберите VK Музыка',
                'Нажмите "Отменить подписку"'
            ],
            'note': 'Также можно отменить через приложение VK в настройках.'
        },
        'apple music': {
            'steps': [
                'Откройте "Настройки" на iPhone',
                'Нажмите на своё имя вверху',
                'Выберите "Подписки"',
                'Найдите Apple Music и нажмите',
                'Нажмите "Отменить подписку"'
            ],
            'note': 'На Android: откройте приложение Apple Music → Настройки → Управление подпиской.'
        },
        'telegram premium': {
            'steps': [
                'Откройте Telegram',
                'Перейдите в Настройки',
                'Нажмите на "Telegram Premium"',
                'Прокрутите вниз до "Управление подпиской"',
                'Отмените через App Store / Google Play'
            ],
            'note': 'Подписка отменяется через магазин приложений, где была оформлена.'
        },
        'okko': {
            'steps': [
                'Откройте okko.tv/account',
                'Перейдите в раздел "Подписка"',
                'Нажмите "Отключить автопродление"',
                'Подтвердите отмену'
            ],
            'note': 'Если подписка через СберПрайм — отменять нужно в приложении СберБанк.'
        },
        'ivi': {
            'steps': [
                'Откройте ivi.ru',
                'Войдите в аккаунт',
                'Перейдите в "Профиль" → "Подписка"',
                'Нажмите "Отменить подписку"'
            ],
            'note': 'При отмене доступ сохранится до конца оплаченного периода.'
        }
    }
    
    guide = guides.get(service, {
        'steps': [
            'Откройте официальный сайт или приложение сервиса',
            'Войдите в свой аккаунт',
            'Найдите раздел "Настройки" или "Профиль"',
            'Перейдите в "Подписка" или "Биллинг"',
            'Нажмите "Отменить подписку" или "Отключить автопродление"'
        ],
        'note': 'Если не получается найти — обратитесь в поддержку сервиса или напишите в чат бота.'
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
        payment_type = data.get('type', 'support')
        
        # Здесь можно сохранить в БД и сгенерировать ссылку на оплату
        # Пока просто возвращаем ссылку на бота
        
        from .config import config
        bot_username = getattr(config, 'BOT_USERNAME', 'your_bot')
        
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
        subscriptions = await db.get_subscriptions(telegram_id)
        
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
        'timestamp': datetime.now().isoformat()
    })


def find_duplicates(subscriptions):
    """Находит дубликаты/пересечения подписок"""
    duplicates = []
    names = [s.get('name', '').lower() for s in subscriptions]
    
    # Яндекс Плюс включает многое
    has_yandex_plus = any('яндекс плюс' in n or 'яндекс+' in n or 'yandex plus' in n for n in names)
    
    if has_yandex_plus:
        for sub in subscriptions:
            name = sub.get('name', '').lower()
            if 'кинопоиск' in name and 'яндекс' not in name:
                duplicates.append({
                    'services': ['Яндекс Плюс', sub.get('name')],
                    'message': 'Кинопоиск уже входит в Яндекс Плюс! Можно сэкономить.',
                    'savings': sub.get('price', 299)
                })
            elif 'яндекс музыка' in name:
                duplicates.append({
                    'services': ['Яндекс Плюс', sub.get('name')],
                    'message': 'Яндекс Музыка уже входит в Яндекс Плюс!',
                    'savings': sub.get('price', 199)
                })
    
    # СберПрайм
    has_sber = any('сберпрайм' in n or 'сбер прайм' in n or 'sberprime' in n for n in names)
    
    if has_sber:
        for sub in subscriptions:
            name = sub.get('name', '').lower()
            if 'okko' in name:
                duplicates.append({
                    'services': ['СберПрайм', sub.get('name')],
                    'message': 'Okko входит в СберПрайм!',
                    'savings': sub.get('price', 399)
                })
            elif 'сберзвук' in name:
                duplicates.append({
                    'services': ['СберПрайм', sub.get('name')],
                    'message': 'СберЗвук входит в СберПрайм!',
                    'savings': sub.get('price', 199)
                })
    
    # МТС Premium
    has_mts = any('мтс premium' in n or 'mts premium' in n for n in names)
    
    if has_mts:
        for sub in subscriptions:
            name = sub.get('name', '').lower()
            if 'kion' in name:
                duplicates.append({
                    'services': ['МТС Premium', sub.get('name')],
                    'message': 'KION входит в МТС Premium!',
                    'savings': sub.get('price', 299)
                })
    
    return duplicates


def create_app():
    """Создаёт и настраивает веб-приложение"""
    app = web.Application()
    
    # CORS middleware
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
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
        
        return middleware_handler
    
    app.middlewares.append(cors_middleware)
    
    # Роуты API
    app.router.add_route('OPTIONS', '/{path:.*}', lambda r: web.Response())  # CORS preflight
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
    logger.info(f"🌐 API сервер запущен на http://{host}:{port}")
    return runner
