#!/bin/bash
set -e

echo "🚀 Starting SubsManager..."

# Инициализация базы данных
echo "📦 Initializing database..."
python scripts/init_db.py

# Запуск миграций
echo "🔄 Running migrations..."
python scripts/migrate.py || true

# Проверка здоровья
echo "🏥 Health check..."
python scripts/check_health.py

# Запуск API сервера в фоне
echo "🌐 Starting API server..."
uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!

# Ждём запуска API
sleep 3

# Запуск бота
echo "🤖 Starting Telegram bot..."
python -m bot.main &
BOT_PID=$!

# Обработка сигналов для graceful shutdown
trap "echo '⏹️ Stopping...'; kill $API_PID $BOT_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# Ждём завершения процессов
wait $API_PID $BOT_PID