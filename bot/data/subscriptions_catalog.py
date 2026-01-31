"""
Каталог популярных российских и международных подписок
"""

SUBSCRIPTION_CATEGORIES = {
    "streaming": "🎬 Видео и ТВ",
    "music": "🎵 Музыка",
    "gaming": "🎮 Игры",
    "books": "📚 Книги и аудио",
    "productivity": "💼 Продуктивность",
    "cloud": "☁️ Облачные сервисы",
    "education": "🎓 Образование",
    "fitness": "💪 Спорт и здоровье",
    "food": "🍔 Еда и доставка",
    "transport": "🚕 Транспорт",
    "communication": "💬 Связь",
    "vpn": "🔒 VPN и безопасность",
    "other": "📦 Другое"
}

# Главный каталог подписок
SUBSCRIPTIONS_CATALOG = {
    # ============ КОМПЛЕКСНЫЕ ПОДПИСКИ ============
    "yandex_plus": {
        "name": "Яндекс Плюс",
        "icon": "🟡",
        "color": "#FFCC00",
        "category": "streaming",
        "default_price": 299,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": ["yandex_music", "kinopoisk", "yandex_disk_bonus", "yandex_afisha"],
        "description": "Музыка, Кинопоиск, кэшбэк, скидки на такси и еду",
        "cancel_url": "https://plus.yandex.ru/manage"
    },
    "yandex_plus_multi": {
        "name": "Яндекс Плюс Мульти",
        "icon": "🟡",
        "color": "#FFCC00",
        "category": "streaming",
        "default_price": 499,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": ["yandex_music", "kinopoisk", "yandex_disk_bonus", "yandex_afisha", "amediateka"],
        "description": "Всё из Плюса + Амедиатека + до 4 аккаунтов",
        "cancel_url": "https://plus.yandex.ru/manage"
    },
    "sber_prime": {
        "name": "СберПрайм",
        "icon": "🟢",
        "color": "#21A038",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": ["sber_zvuk", "okko", "sber_disk"],
        "description": "Окко, СберЗвук, скидки и кэшбэк",
        "cancel_url": "https://www.sberbank.ru/prime"
    },
    "mts_premium": {
        "name": "МТС Premium",
        "icon": "🔴",
        "color": "#E30611",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly"],
        "included_services": ["mts_music", "kion", "mts_library"],
        "description": "KION, МТС Музыка, книги, связь",
        "cancel_url": "https://premium.mts.ru"
    },
    "tinkoff_pro": {
        "name": "Тинькофф Pro",
        "icon": "🟡",
        "color": "#FFDD2D",
        "category": "other",
        "default_price": 399,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Кэшбэк, бесплатные переводы и снятия",
        "cancel_url": "https://www.tinkoff.ru/pro/"
    },
    "vk_combo": {
        "name": "VK Combo",
        "icon": "🔵",
        "color": "#0077FF",
        "category": "streaming",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": ["vk_music", "vk_video"],
        "description": "Музыка ВК, скидки на сервисы VK",
        "cancel_url": "https://combo.vk.ru"
    },
    
    # ============ ВИДЕО И ТВ ============
    "kinopoisk": {
        "name": "Кинопоиск",
        "icon": "🎬",
        "color": "#FF6600",
        "category": "streaming",
        "default_price": 269,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фильмы, сериалы, ТВ-каналы",
        "cancel_url": "https://hd.kinopoisk.ru/settings"
    },
    "ivi": {
        "name": "Иви",
        "icon": "🟣",
        "color": "#EA1E63",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фильмы, сериалы, мультфильмы",
        "cancel_url": "https://www.ivi.ru/profile/subscription"
    },
    "okko": {
        "name": "Okko",
        "icon": "🟣",
        "color": "#6B3FA0",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фильмы, сериалы, спорт",
        "cancel_url": "https://okko.tv/settings/subscription"
    },
    "kion": {
        "name": "KION",
        "icon": "🔴",
        "color": "#E30611",
        "category": "streaming",
        "default_price": 299,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фильмы, сериалы от МТС",
        "cancel_url": "https://kion.ru/settings"
    },
    "premier": {
        "name": "PREMIER",
        "icon": "🔴",
        "color": "#FF0000",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Контент ТНТ, ТВ-3 и другие",
        "cancel_url": "https://premier.one/settings/subscription"
    },
    "wink": {
        "name": "Wink",
        "icon": "🟣",
        "color": "#7B2D8E",
        "category": "streaming",
        "default_price": 299,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фильмы, сериалы, ТВ от Ростелеком",
        "cancel_url": "https://wink.ru/settings"
    },
    "amediateka": {
        "name": "Амедиатека",
        "icon": "⬛",
        "color": "#000000",
        "category": "streaming",
        "default_price": 599,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "HBO, эксклюзивные сериалы",
        "cancel_url": "https://www.amediateka.ru/account"
    },
    "start": {
        "name": "START",
        "icon": "🟠",
        "color": "#FF6B00",
        "category": "streaming",
        "default_price": 399,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Российские фильмы и сериалы",
        "cancel_url": "https://start.ru/settings"
    },
    "more_tv": {
        "name": "more.tv",
        "icon": "🔵",
        "color": "#0066FF",
        "category": "streaming",
        "default_price": 299,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Сериалы, фильмы, шоу",
        "cancel_url": "https://more.tv/profile"
    },
    
    # ============ МУЗЫКА ============
    "yandex_music": {
        "name": "Яндекс Музыка",
        "icon": "🎵",
        "color": "#FFCC00",
        "category": "music",
        "default_price": 249,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Музыка, подкасты, радио",
        "note": "Входит в Яндекс Плюс",
        "cancel_url": "https://music.yandex.ru/settings"
    },
    "vk_music": {
        "name": "VK Музыка",
        "icon": "🎵",
        "color": "#0077FF",
        "category": "music",
        "default_price": 169,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Музыка без рекламы, оффлайн",
        "cancel_url": "https://vk.com/settings?act=payments"
    },
    "spotify": {
        "name": "Spotify",
        "icon": "🟢",
        "color": "#1DB954",
        "category": "music",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Музыка, подкасты",
        "cancel_url": "https://www.spotify.com/account"
    },
    "apple_music": {
        "name": "Apple Music",
        "icon": "🍎",
        "color": "#FA2D48",
        "category": "music",
        "default_price": 199,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Музыка Apple",
        "cancel_url": "https://support.apple.com/ru-ru/HT202039"
    },
    "sber_zvuk": {
        "name": "СберЗвук",
        "icon": "🎵",
        "color": "#21A038",
        "category": "music",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Музыка от Сбера",
        "cancel_url": "https://sberzvuk.com/settings"
    },
    "mts_music": {
        "name": "МТС Музыка",
        "icon": "🎵",
        "color": "#E30611",
        "category": "music",
        "default_price": 169,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Музыка от МТС",
        "cancel_url": "https://music.mts.ru/settings"
    },
    "zvuk": {
        "name": "Звук",
        "icon": "🎵",
        "color": "#6B3FA0",
        "category": "music",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Музыка, подкасты",
        "cancel_url": "https://zvuk.com/settings"
    },
    
    # ============ ИГРЫ ============
    "xbox_game_pass": {
        "name": "Xbox Game Pass",
        "icon": "🎮",
        "color": "#107C10",
        "category": "gaming",
        "default_price": 699,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Библиотека игр Xbox и PC",
        "cancel_url": "https://account.microsoft.com/services"
    },
    "ps_plus": {
        "name": "PlayStation Plus",
        "icon": "🎮",
        "color": "#003087",
        "category": "gaming",
        "default_price": 899,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Онлайн, бесплатные игры",
        "cancel_url": "https://www.playstation.com/settings"
    },
    "vk_play": {
        "name": "VK Play",
        "icon": "🎮",
        "color": "#0077FF",
        "category": "gaming",
        "default_price": 299,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Облачный гейминг от VK",
        "cancel_url": "https://vkplay.ru/settings"
    },
    "geforce_now": {
        "name": "GeForce NOW",
        "icon": "🟢",
        "color": "#76B900",
        "category": "gaming",
        "default_price": 999,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Облачный гейминг Nvidia",
        "cancel_url": "https://www.nvidia.com/account"
    },
    
    # ============ КНИГИ И АУДИО ============
    "litres": {
        "name": "Литрес Подписка",
        "icon": "📚",
        "color": "#FF6B00",
        "category": "books",
        "default_price": 399,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Книги, аудиокниги",
        "cancel_url": "https://www.litres.ru/pages/my_subscription/"
    },
    "bookmate": {
        "name": "Bookmate",
        "icon": "📖",
        "color": "#FF5722",
        "category": "books",
        "default_price": 299,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Книги, аудиокниги, комиксы",
        "cancel_url": "https://bookmate.com/settings"
    },
    "mybook": {
        "name": "MyBook",
        "icon": "📚",
        "color": "#00A8E8",
        "category": "books",
        "default_price": 399,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Электронные и аудиокниги",
        "cancel_url": "https://mybook.ru/settings/"
    },
    "storytel": {
        "name": "Storytel",
        "icon": "🎧",
        "color": "#FF6B35",
        "category": "books",
        "default_price": 549,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Аудиокниги",
        "cancel_url": "https://www.storytel.com/settings"
    },
    
    # ============ ПРОДУКТИВНОСТЬ ============
    "notion": {
        "name": "Notion",
        "icon": "📝",
        "color": "#000000",
        "category": "productivity",
        "default_price": 800,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Заметки, базы данных, wiki",
        "cancel_url": "https://www.notion.so/my-account"
    },
    "evernote": {
        "name": "Evernote",
        "icon": "🐘",
        "color": "#00A82D",
        "category": "productivity",
        "default_price": 600,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Заметки и организация",
        "cancel_url": "https://www.evernote.com/Settings.action"
    },
    "todoist": {
        "name": "Todoist",
        "icon": "✅",
        "color": "#E44332",
        "category": "productivity",
        "default_price": 339,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Менеджер задач",
        "cancel_url": "https://todoist.com/app/settings/subscription"
    },
    
    # ============ ОБЛАЧНЫЕ СЕРВИСЫ ============
    "yandex_disk": {
        "name": "Яндекс Диск",
        "icon": "☁️",
        "color": "#FFCC00",
        "category": "cloud",
        "default_price": 99,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Облачное хранилище",
        "cancel_url": "https://disk.yandex.ru/client/settings"
    },
    "mail_cloud": {
        "name": "Облако Mail.ru",
        "icon": "☁️",
        "color": "#005FF9",
        "category": "cloud",
        "default_price": 99,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Облачное хранилище",
        "cancel_url": "https://cloud.mail.ru/home"
    },
    "icloud": {
        "name": "iCloud+",
        "icon": "☁️",
        "color": "#3693F3",
        "category": "cloud",
        "default_price": 99,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Облако Apple",
        "cancel_url": "https://support.apple.com/icloud"
    },
    "google_one": {
        "name": "Google One",
        "icon": "☁️",
        "color": "#4285F4",
        "category": "cloud",
        "default_price": 139,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Облако Google",
        "cancel_url": "https://one.google.com/settings"
    },
    
    # ============ ОБРАЗОВАНИЕ ============
    "skillbox": {
        "name": "Skillbox",
        "icon": "🎓",
        "color": "#6B4FBB",
        "category": "education",
        "default_price": 3500,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Онлайн-курсы",
        "cancel_url": "https://skillbox.ru/settings/"
    },
    "geekbrains": {
        "name": "GeekBrains",
        "icon": "🎓",
        "color": "#6AAF1C",
        "category": "education",
        "default_price": 3000,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "IT-образование",
        "cancel_url": "https://geekbrains.ru/settings"
    },
    "skyeng": {
        "name": "Skyeng",
        "icon": "🇬🇧",
        "color": "#00C2FF",
        "category": "education",
        "default_price": 1500,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Английский онлайн",
        "cancel_url": "https://skyeng.ru/personal"
    },
    "duolingo": {
        "name": "Duolingo Plus",
        "icon": "🦉",
        "color": "#58CC02",
        "category": "education",
        "default_price": 699,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Изучение языков",
        "cancel_url": "https://www.duolingo.com/settings/subscription"
    },
    
    # ============ СПОРТ И ЗДОРОВЬЕ ============
    "strava": {
        "name": "Strava",
        "icon": "🏃",
        "color": "#FC4C02",
        "category": "fitness",
        "default_price": 479,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Трекер тренировок",
        "cancel_url": "https://www.strava.com/settings/subscription"
    },
    "fitbit_premium": {
        "name": "Fitbit Premium",
        "icon": "💪",
        "color": "#00B0B9",
        "category": "fitness",
        "default_price": 699,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Фитнес и здоровье",
        "cancel_url": "https://www.fitbit.com/settings"
    },
    
    # ============ ЕДА И ДОСТАВКА ============
    "yandex_eda_plus": {
        "name": "Яндекс Еда (Плюс)",
        "icon": "🍔",
        "color": "#FFCC00",
        "category": "food",
        "default_price": 0,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Скидки входят в Яндекс Плюс",
        "note": "Входит в Яндекс Плюс"
    },
    "samokat": {
        "name": "Самокат Плюс",
        "icon": "🛴",
        "color": "#00CC66",
        "category": "food",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Бесплатная доставка",
        "cancel_url": "https://samokat.ru"
    },
    "delivery_club": {
        "name": "Delivery Club Premium",
        "icon": "🍕",
        "color": "#28A745",
        "category": "food",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Бесплатная доставка еды",
        "cancel_url": "https://www.delivery-club.ru"
    },
    
    # ============ ТРАНСПОРТ ============
    "yandex_taxi": {
        "name": "Яндекс Go (подписка)",
        "icon": "🚕",
        "color": "#FFCC00",
        "category": "transport",
        "default_price": 199,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Скидки на такси",
        "cancel_url": "https://taxi.yandex.ru"
    },
    "citydrive": {
        "name": "Ситидрайв",
        "icon": "🚗",
        "color": "#6B3FA0",
        "category": "transport",
        "default_price": 0,
        "billing_cycles": ["monthly"],
        "included_services": [],
        "description": "Каршеринг (пакеты минут)",
        "cancel_url": "https://citydrive.ru"
    },
    
    # ============ VPN И БЕЗОПАСНОСТЬ ============
    "kaspersky": {
        "name": "Kaspersky",
        "icon": "🛡️",
        "color": "#006D5C",
        "category": "vpn",
        "default_price": 299,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Антивирус и VPN",
        "cancel_url": "https://my.kaspersky.com"
    },
    "nordvpn": {
        "name": "NordVPN",
        "icon": "🔒",
        "color": "#4687FF",
        "category": "vpn",
        "default_price": 550,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "VPN-сервис",
        "cancel_url": "https://my.nordaccount.com"
    },
    
    # ============ СВЯЗЬ ============
    "telegram_premium": {
        "name": "Telegram Premium",
        "icon": "⭐",
        "color": "#0088CC",
        "category": "communication",
        "default_price": 299,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Премиум Telegram",
        "cancel_url": "https://t.me/settings"
    },
    "zoom": {
        "name": "Zoom Pro",
        "icon": "📹",
        "color": "#2D8CFF",
        "category": "communication",
        "default_price": 1100,
        "billing_cycles": ["monthly", "yearly"],
        "included_services": [],
        "description": "Видеоконференции",
        "cancel_url": "https://zoom.us/account"
    }
}

def get_subscription_by_id(service_id: str) -> dict:
    """Получить подписку по ID"""
    return SUBSCRIPTIONS_CATALOG.get(service_id)

def get_subscriptions_by_category(category: str) -> list:
    """Получить подписки по категории"""
    return [
        {"id": k, **v} 
        for k, v in SUBSCRIPTIONS_CATALOG.items() 
        if v.get("category") == category
    ]

def search_subscriptions(query: str) -> list:
    """Поиск подписок"""
    query = query.lower()
    results = []
    for k, v in SUBSCRIPTIONS_CATALOG.items():
        if query in v["name"].lower() or query in k:
            results.append({"id": k, **v})
    return results

def get_all_categories() -> dict:
    """Получить все категории"""
    return SUBSCRIPTION_CATEGORIES