/**
 * SubsManager Mini App
 * Современное приложение для управления подписками
 */

// ============ CONFIGURATION ============
const CONFIG = {
    API_URL: window.location.origin + '/api',
    DEBUG: false
};

// ============ TELEGRAM WEB APP ============
const tg = window.Telegram?.WebApp;

// ============ STATE ============
let state = {
    user: null,
    subscriptions: [],
    analytics: null,
    tips: [],
    duplicates: [],
    currentTab: 'subscriptions',
    selectedSubscription: null
};

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', async () => {
    // Инициализация Telegram Web App
    if (tg) {
        tg.ready();
        tg.expand();
        
        // Применяем тему Telegram
        applyTelegramTheme();
        
        // Получаем данные пользователя
        if (tg.initDataUnsafe?.user) {
            state.user = tg.initDataUnsafe.user;
        }
    }
    
    // Загружаем данные
    await loadData();
    
    // Инициализируем UI
    initUI();
    
    // Скрываем loader
    hideLoader();
});

function applyTelegramTheme() {
    if (!tg) return;
    
    const root = document.documentElement;
    
    // Определяем тему
    if (tg.colorScheme === 'light') {
        document.body.classList.add('light-theme');
    }
    
    // Применяем цвета Telegram
    if (tg.themeParams) {
        const params = tg.themeParams;
        
        if (params.bg_color) {
            root.style.setProperty('--bg-primary', params.bg_color);
        }
        if (params.secondary_bg_color) {
            root.style.setProperty('--bg-secondary', params.secondary_bg_color);
        }
        if (params.text_color) {
            root.style.setProperty('--text-primary', params.text_color);
        }
        if (params.hint_color) {
            root.style.setProperty('--text-secondary', params.hint_color);
        }
        if (params.button_color) {
            root.style.setProperty('--accent-primary', params.button_color);
        }
    }
}

// ============ DATA LOADING ============
async function loadData() {
    const telegramId = state.user?.id || getTestUserId();
    
    if (!telegramId) {
        console.error('No user ID available');
        return;
    }
    
    try {
        // Параллельная загрузка
        const [subsResponse, analyticsResponse] = await Promise.all([
            fetch(`${CONFIG.API_URL}/user/${telegramId}/subscriptions`),
            fetch(`${CONFIG.API_URL}/user/${telegramId}/analytics`)
        ]);
        
        if (subsResponse.ok) {
            const data = await subsResponse.json();
            state.subscriptions = data.subscriptions || [];
        }
        
        if (analyticsResponse.ok) {
            state.analytics = await analyticsResponse.json();
            state.tips = state.analytics.tips || [];
        }
        
        // Загружаем дубликаты
        const duplicatesResponse = await fetch(`${CONFIG.API_URL}/user/${telegramId}/duplicates`);
        if (duplicatesResponse.ok) {
            const dupData = await duplicatesResponse.json();
            state.duplicates = dupData.duplicates || [];
        }
        
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Ошибка загрузки данных', 'error');
    }
}

function getTestUserId() {
    // Для тестирования без Telegram
    return new URLSearchParams(window.location.search).get('user_id') || null;
}

// ============ UI INITIALIZATION ============
function initUI() {
    // Обновляем header
    updateHeader();
    
    // Обновляем статистику
    updateStats();
    
    // Рендерим подписки
    renderSubscriptions();
    
    // Рендерим аналитику
    renderAnalytics();
    
    // Рендерим советы
    renderTips();
    
    // Инициализируем события
    initEventListeners();
}

function updateHeader() {
    const userName = state.user?.first_name || 'друг';
    const userInitial = userName.charAt(0).toUpperCase();
    
    document.getElementById('userName').textContent = userName;
    document.getElementById('userInitial').textContent = userInitial;
    
    // Обновляем подзаголовок
    const subsCount = state.subscriptions.length;
    let subtitle = 'Управляй подписками';
    
    if (subsCount > 0) {
        subtitle = `${subsCount} ${pluralize(subsCount, ['подписка', 'подписки', 'подписок'])}`;
    }
    
    document.getElementById('headerSubtitle').textContent = subtitle;
}

function updateStats() {
    const analytics = state.analytics || {};
    
    // Месячные траты
    const monthlyTotal = analytics.total_monthly || 0;
    animateValue('monthlyTotal', monthlyTotal, '₽');
    
    // Годовые траты
    const yearlyTotal = analytics.total_yearly || 0;
    animateValue('yearlyTotal', yearlyTotal, '₽');
    
    // Количество подписок
    const subsCount = analytics.subscriptions_count || 0;
    animateValue('subsCount', subsCount);
    
    // Потенциальная экономия
    const potentialSavings = state.tips.reduce((sum, tip) => sum + (tip.potential_saving || 0), 0);
    if (potentialSavings > 0) {
        animateValue('potentialSavings', potentialSavings, '₽');
        document.getElementById('savingsCard').classList.remove('hidden');
    } else {
        document.getElementById('savingsCard').classList.add('hidden');
    }
    
    // Прогнозы
    document.getElementById('quarterlyForecast').textContent = formatCurrency(monthlyTotal * 3);
    document.getElementById('yearlyForecast').textContent = formatCurrency(yearlyTotal);
    document.getElementById('fiveYearForecast').textContent = formatCurrency(yearlyTotal * 5);
}

// ============ SUBSCRIPTIONS ============
function renderSubscriptions() {
    const container = document.getElementById('subscriptionsList');
    const emptyState = document.getElementById('emptyState');
    
    if (state.subscriptions.length === 0) {
        container.classList.add('hidden');
        emptyState.classList.remove('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    emptyState.classList.add('hidden');
    
    container.innerHTML = state.subscriptions.map(sub => createSubscriptionCard(sub)).join('');
    
    // Добавляем обработчики кликов
    container.querySelectorAll('.subscription-card').forEach(card => {
        card.addEventListener('click', () => {
            const subId = parseInt(card.dataset.id);
            openSubscriptionDetail(subId);
        });
    });
}

function createSubscriptionCard(sub) {
    const icon = sub.icon || getDefaultIcon(sub.category);
    const statusClass = sub.is_trial ? 'trial' : sub.status;
    const statusText = getStatusText(sub);
    const cycleText = getCycleText(sub.billing_cycle);
    
    let cardClass = 'subscription-card';
    if (sub.is_trial) cardClass += ' trial';
    
    return `
        <div class="${cardClass}" data-id="${sub.id}">
            <div class="sub-icon" style="background: ${sub.color || 'var(--bg-tertiary)'}20">
                ${icon}
            </div>
            <div class="sub-info">
                <div class="sub-name">${escapeHtml(sub.name)}</div>
                <div class="sub-meta">
                    <span class="sub-status ${statusClass}">${statusText}</span>
                    ${sub.next_billing_date ? `<span>• ${formatDate(sub.next_billing_date)}</span>` : ''}
                </div>
            </div>
            <div class="sub-price">
                <div class="sub-price-value">${formatCurrency(sub.price)}</div>
                <div class="sub-price-cycle">${cycleText}</div>
            </div>
        </div>
    `;
}

function openSubscriptionDetail(subId) {
    const sub = state.subscriptions.find(s => s.id === subId);
    if (!sub) return;
    
    state.selectedSubscription = sub;
    
    const modal = document.getElementById('subDetailModal');
    const title = document.getElementById('detailTitle');
    const body = document.getElementById('detailBody');
    
    title.textContent = sub.name;
    
    body.innerHTML = `
        <div class="detail-content">
            <div class="detail-icon" style="background: ${sub.color || 'var(--bg-tertiary)'}20">
                ${sub.icon || getDefaultIcon(sub.category)}
            </div>
            
            <div class="detail-stats">
                <div class="detail-stat">
                    <span class="detail-label">Стоимость</span>
                    <span class="detail-value">${formatCurrency(sub.price)} / ${getCycleText(sub.billing_cycle)}</span>
                </div>
                <div class="detail-stat">
                    <span class="detail-label">В месяц</span>
                    <span class="detail-value">~${formatCurrency(getMonthlyPrice(sub))}</span>
                </div>
                <div class="detail-stat">
                    <span class="detail-label">Статус</span>
                    <span class="detail-value">${getStatusText(sub)}</span>
                </div>
                ${sub.next_billing_date ? `
                    <div class="detail-stat">
                        <span class="detail-label">Следующее списание</span>
                        <span class="detail-value">${formatDate(sub.next_billing_date)}</span>
                    </div>
                ` : ''}
                ${sub.is_trial && sub.trial_end_date ? `
                    <div class="detail-stat warning">
                        <span class="detail-label">⏱️ Триал до</span>
                        <span class="detail-value">${formatDate(sub.trial_end_date)}</span>
                    </div>
                ` : ''}
                ${sub.notes ? `
                    <div class="detail-stat">
                        <span class="detail-label">Заметка</span>
                        <span class="detail-value">${escapeHtml(sub.notes)}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    modal.classList.remove('hidden');
    
    // Настраиваем кнопки
    document.getElementById('deleteSubBtn').onclick = () => deleteSubscription(subId);
    document.getElementById('editSubBtn').onclick = () => editSubscription(subId);
}

async function deleteSubscription(subId) {
    if (!confirm('Удалить эту подписку?')) return;
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/subscriptions/${subId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            state.subscriptions = state.subscriptions.filter(s => s.id !== subId);
            renderSubscriptions();
            closeModal('subDetailModal');
            showToast('Подписка удалена', 'success');
            
            // Обновляем статистику
            await loadData();
            updateStats();
        } else {
            throw new Error('Failed to delete');
        }
    } catch (error) {
        console.error('Error deleting subscription:', error);
        showToast('Ошибка удаления', 'error');
    }
}

function editSubscription(subId) {
    // TODO: Реализовать редактирование
    showToast('Редактирование скоро будет доступно', 'warning');
}

// ============ ANALYTICS ============
function renderAnalytics() {
    renderCategoriesChart();
    renderCategoriesList();
}

function renderCategoriesChart() {
    const canvas = document.getElementById('categoriesChart');
    const ctx = canvas.getContext('2d');
    
    const categories = state.analytics?.by_category || [];
    
    if (categories.length === 0) {
        return;
    }
    
    const colors = [
        '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
        '#ec4899', '#f43f5e', '#f97316', '#eab308'
    ];
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categories.map(c => c.category_name),
            datasets: [{
                data: categories.map(c => c.amount),
                backgroundColor: colors.slice(0, categories.length),
                borderWidth: 0,
                spacing: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            return `${context.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

function renderCategoriesList() {
    const container = document.getElementById('categoriesList');
    const categories = state.analytics?.by_category || [];
    
    if (categories.length === 0) {
        container.innerHTML = '<p class="empty-message">Нет данных по категориям</p>';
        return;
    }
    
    const maxAmount = Math.max(...categories.map(c => c.amount));
    
    container.innerHTML = categories.map(cat => `
        <div class="category-item">
            <span class="category-emoji">${cat.emoji}</span>
            <div class="category-info">
                <div class="category-name">${cat.category_name}</div>
                <div class="category-bar">
                    <div class="category-bar-fill" style="width: ${(cat.amount / maxAmount) * 100}%"></div>
                </div>
            </div>
            <div class="category-stats">
                <span class="category-amount">${formatCurrency(cat.amount)}</span>
                <span class="category-percent">${cat.percent.toFixed(0)}%</span>
            </div>
        </div>
    `).join('');
}

// ============ TIPS ============
function renderTips() {
    const container = document.getElementById('tipsList');
    const duplicatesCard = document.getElementById('duplicatesCard');
    
    if (state.tips.length === 0) {
        container.innerHTML = `
            <div class="empty-message">
                <p>✨ Отлично! Советов по оптимизации пока нет.</p>
            </div>
        `;
    } else {
        container.innerHTML = state.tips.map(tip => createTipCard(tip)).join('');
    }
    
    // Дубликаты
    if (state.duplicates.length > 0) {
        duplicatesCard.classList.remove('hidden');
        document.getElementById('duplicatesCount').textContent = 
            `${state.duplicates.length} ${pluralize(state.duplicates.length, ['пересечение', 'пересечения', 'пересечений'])}`;
    } else {
        duplicatesCard.classList.add('hidden');
    }
}

function createTipCard(tip) {
    const priorityClass = tip.priority || 'medium';
    const priorityEmoji = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    }[priorityClass] || '💡';
    
    return `
        <div class="tip-card ${priorityClass}">
            <div class="tip-header">
                <span class="tip-priority">${priorityEmoji}</span>
                <span class="tip-title">${escapeHtml(tip.title)}</span>
            </div>
            <p class="tip-description">${escapeHtml(tip.description)}</p>
            ${tip.potential_saving > 0 ? `
                <span class="tip-saving">💰 Экономия: ~${formatCurrency(tip.potential_saving)}/мес</span>
            ` : ''}
        </div>
    `;
}

// ============ ADD SUBSCRIPTION ============
function openAddModal() {
    document.getElementById('addSubModal').classList.remove('hidden');
    document.getElementById('addSubForm').reset();
    document.getElementById('trialEndGroup').classList.add('hidden');
}

async function handleAddSubscription(event) {
    event.preventDefault();
    
    const form = event.target;
    const telegramId = state.user?.id || getTestUserId();
    
    const data = {
        name: form.subName.value.trim(),
        price: parseFloat(form.subPrice.value),
        billing_cycle: form.subCycle.value,
        category: form.subCategory.value,
        is_trial: form.subIsTrial.checked,
        trial_end_date: form.subIsTrial.checked ? form.subTrialEnd.value : null
    };
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/user/${telegramId}/subscriptions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('addSubModal');
            showToast('Подписка добавлена!', 'success');
            
            // Перезагружаем данные
            await loadData();
            updateStats();
            renderSubscriptions();
            
            // Haptic feedback
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        } else {
            throw new Error('Failed to add subscription');
        }
    } catch (error) {
        console.error('Error adding subscription:', error);
        showToast('Ошибка добавления', 'error');
    }
}

async function quickAddSubscription(serviceId) {
    const telegramId = state.user?.id || getTestUserId();
    
    // Данные популярных сервисов
    const services = {
        'yandex_plus': { name: 'Яндекс Плюс', price: 299, category: 'streaming' },
        'vk_combo': { name: 'VK Combo', price: 199, category: 'streaming' },
        'kinopoisk': { name: 'Кинопоиск', price: 269, category: 'streaming' },
        'telegram_premium': { name: 'Telegram Premium', price: 299, category: 'communication' }
    };
    
    const service = services[serviceId];
    if (!service) return;
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/user/${telegramId}/subscriptions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ...service,
                billing_cycle: 'monthly'
            })
        });
        
        if (response.ok) {
            closeModal('addSubModal');
            showToast(`${service.name} добавлен!`, 'success');
            
            await loadData();
            updateStats();
            renderSubscriptions();
            
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Ошибка добавления', 'error');
    }
}

// ============ EVENT LISTENERS ============
function initEventListeners() {
    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
    // FAB & Add buttons
    document.getElementById('fabBtn').addEventListener('click', openAddModal);
    document.getElementById('addSubBtn').addEventListener('click', openAddModal);
    document.getElementById('addFirstSubBtn')?.addEventListener('click', openAddModal);
    
    // Modal close buttons
    document.getElementById('closeModalBtn').addEventListener('click', () => closeModal('addSubModal'));
    document.getElementById('closeDetailBtn').addEventListener('click', () => closeModal('subDetailModal'));
    
    // Modal backdrop clicks
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => {
            closeModal('addSubModal');
            closeModal('subDetailModal');
        });
    });
    
    // Add form
    document.getElementById('addSubForm').addEventListener('submit', handleAddSubscription);
    
    // Trial checkbox
    document.getElementById('subIsTrial').addEventListener('change', (e) => {
        document.getElementById('trialEndGroup').classList.toggle('hidden', !e.target.checked);
    });
    
    // Quick add services
    document.querySelectorAll('.quick-service').forEach(btn => {
        btn.addEventListener('click', () => quickAddSubscription(btn.dataset.service));
    });
    
    // Settings button
    document.getElementById('settingsBtn').addEventListener('click', () => {
        if (tg) {
            tg.close();
        }
    });
    
    // View duplicates
    document.getElementById('viewDuplicatesBtn')?.addEventListener('click', () => {
        showToast('Посмотри дубликаты в боте', 'info');
        if (tg) tg.close();
    });
}

function switchTab(tabId) {
    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabId}-tab`);
    });
    
    state.currentTab = tabId;
    
    // Haptic feedback
    if (tg?.HapticFeedback) {
        tg.HapticFeedback.selectionChanged();
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// ============ UTILITIES ============
function hideLoader() {
    const loader = document.getElementById('loader');
    const app = document.getElementById('app');
    
    loader.classList.add('hidden');
    app.classList.remove('hidden');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'decimal',
        maximumFractionDigits: 0
    }).format(amount) + '₽';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function pluralize(n, forms) {
    const n10 = n % 10;
    const n100 = n % 100;
    
    if (n10 === 1 && n100 !== 11) return forms[0];
    if (n10 >= 2 && n10 <= 4 && (n100 < 10 || n100 >= 20)) return forms[1];
    return forms[2];
}

function animateValue(elementId, value, suffix = '') {
    const element = document.getElementById(elementId);
    const duration = 500;
    const start = 0;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (value - start) * easeOut);
        
        element.textContent = formatCurrency(current).replace('₽', '') + suffix;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function getDefaultIcon(category) {
    const icons = {
        'streaming': '🎬',
        'music': '🎵',
        'gaming': '🎮',
        'books': '📚',
        'productivity': '💼',
        'cloud': '☁️',
        'education': '🎓',
        'fitness': '💪',
        'food': '🍔',
        'transport': '🚕',
        'communication': '💬',
        'vpn': '🔒',
        'other': '📦'
    };
    return icons[category] || '📦';
}

function getStatusText(sub) {
    if (sub.is_trial) return 'Триал';
    const statuses = {
        'active': 'Активна',
        'paused': 'Пауза',
        'cancelled': 'Отменена'
    };
    return statuses[sub.status] || sub.status;
}

function getCycleText(cycle) {
    const cycles = {
        'weekly': 'нед',
        'monthly': 'мес',
        'quarterly': 'квартал',
        'yearly': 'год'
    };
    return cycles[cycle] || cycle;
}

function getMonthlyPrice(sub) {
    const multipliers = {
        'weekly': 4.33,
        'monthly': 1,
        'quarterly': 1/3,
        'yearly': 1/12
    };
    return sub.price * (multipliers[sub.billing_cycle] || 1);
}

// ============ TELEGRAM MAIN BUTTON ============
if (tg) {
    // Настраиваем главную кнопку
    tg.MainButton.setParams({
        text: 'Добавить подписку',
        color: '#6366f1',
        text_color: '#ffffff'
    });
    
    tg.MainButton.onClick(openAddModal);
    
    // Показываем кнопку на вкладке подписок
    // tg.MainButton.show();
}