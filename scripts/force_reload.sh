#!/bin/bash
"""
Force Reload Development Server
Спира текущия Flask сървър и го стартира отново с принудително обновяване
"""

echo "🔄 Force reloading WebPortal development server..."

# Спиране на всички Flask процеси на порт 5001
echo "🛑 Stopping existing Flask processes on port 5001..."
lsof -ti:5001 | xargs -r kill -9

# Почакване малко да се освободи портът
sleep 2

# Активиране на виртуалната среда
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Изчистване на Python cache файлове
echo "🧹 Clearing Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Задаване на environment променливи за принудително обновяване
export FLASK_ENV=development
export FLASK_DEBUG=1
export TEMPLATES_AUTO_RELOAD=1

echo "🚀 Starting WebPortal with forced template reloading..."
echo "📁 All templates and static files will auto-reload"
echo "🔄 Browser cache is disabled"
echo "-" * 50

python run_debug.py