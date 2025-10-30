#!/bin/bash
"""
Quick Setup Script
Инициализира базата данни и създава администратор за WebPortal
"""

set -e

echo "🚀 WebPortal Quick Setup"
echo "======================="

# Активиране на виртуалната среда ако съществува
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Експорт на Flask приложението
export FLASK_APP=webportal.py

echo "🗄️  Running database migrations..."
flask db upgrade

echo ""
echo "👤 Creating default administrator..."
python scripts/create_admin.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🌐 You can now access WebPortal at:"
echo "   - Web interface: http://localhost:5001"
echo "   - Admin panel: http://localhost:5001/admin"
echo ""
echo "🔐 Default login credentials:"
echo "   - Email: admin@webportal.local"
echo "   - Password: admin123"
echo ""
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo ""
echo "📝 To start the application:"
echo "   python run_debug.py    # Development mode"
echo "   python webportal.py     # Production mode"