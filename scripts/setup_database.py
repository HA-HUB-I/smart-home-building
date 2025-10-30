#!/usr/bin/env python3
"""
WebPortal Database Setup Script
Автоматично създава и инициализира базата данни с всички необходими данни
"""

import os
import sys
import subprocess
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import getpass

def print_header():
    print("=" * 60)
    print("🏢 WebPortal Database Setup Script")
    print("=" * 60)
    print()

def print_step(step, description):
    print(f"🔧 Step {step}: {description}")
    print("-" * 40)

def run_command(command, description="", check=True):
    """Изпълнява команда и показва резултата"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(f"✅ {description}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_postgresql():
    """Проверява дали PostgreSQL е инсталиран и работи"""
    print_step(1, "Checking PostgreSQL installation")
    
    # Проверка дали PostgreSQL е инсталиран
    if not run_command("which psql", "PostgreSQL client found", check=False):
        print("❌ PostgreSQL is not installed!")
        print("Please install PostgreSQL first:")
        print("Ubuntu/Debian:  apt install postgresql postgresql-contrib")
        print("CentOS/RHEL:  dnf install postgresql postgresql-server")
        return False
    
    # Проверка дали PostgreSQL service работи
    if not run_command(" systemctl is-active postgresql", "PostgreSQL service is running", check=False):
        print("🔄 Starting PostgreSQL service...")
        if not run_command(" systemctl start postgresql", "PostgreSQL service started"):
            print("❌ Failed to start PostgreSQL service!")
            return False
    
    print("✅ PostgreSQL is ready")
    return True

def get_database_config():
    """Получава конфигурацията за базата данни от потребителя"""
    print_step(2, "Database Configuration")
    
    config = {}
    
    print("Enter database configuration (press Enter for default values):")
    config['host'] = input("Database host [localhost]: ") or "localhost"
    config['port'] = input("Database port [5432]: ") or "5432"
    config['admin_user'] = input("PostgreSQL admin user [postgres]: ") or "postgres"
    config['db_name'] = input("Database name [webportal]: ") or "webportal_home"
    config['db_user'] = input("Database user [webportal_user]: ") or "webportalhome_user"
    config['db_password'] = getpass.getpass("Database user password: ")
    
    if not config['db_password']:
        print("❌ Password is required!")
        return None
    
    return config

def create_database_and_user(config):
    """Създава базата данни и потребителя"""
    print_step(3, "Creating database and user")
    
    try:
        # Свързване като admin потребител
        admin_password = getpass.getpass(f"Enter password for PostgreSQL user '{config['admin_user']}': ")
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['admin_user'],
            password=admin_password,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверка дали потребителят съществува
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (config['db_user'],))
        if not cursor.fetchone():
            print(f"Creating user '{config['db_user']}'...")
            cursor.execute(f"""
                CREATE USER {config['db_user']} WITH PASSWORD %s;
            """, (config['db_password'],))
            print(f"✅ User '{config['db_user']}' created")
        else:
            print(f"ℹ️  User '{config['db_user']}' already exists")
            # Обновяване на паролата
            cursor.execute(f"ALTER USER {config['db_user']} WITH PASSWORD %s", (config['db_password'],))
        
        # Проверка дали базата данни съществува
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config['db_name'],))
        if not cursor.fetchone():
            print(f"Creating database '{config['db_name']}'...")
            cursor.execute(f"CREATE DATABASE {config['db_name']} OWNER {config['db_user']};")
            print(f"✅ Database '{config['db_name']}' created")
        else:
            print(f"ℹ️  Database '{config['db_name']}' already exists")
        
        # Даване на права
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {config['db_name']} TO {config['db_user']};")
        cursor.execute(f"ALTER USER {config['db_user']} CREATEDB;")
        
        cursor.close()
        conn.close()
        
        print("✅ Database and user setup completed")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def setup_environment_file(config):
    """Създава или обновява .env файла"""
    print_step(4, "Setting up environment file")
    
    env_file = Path(".env")
    env_template = Path("env.template")
    
    # Четене на template файла
    if env_template.exists():
        with open(env_template, 'r') as f:
            template_content = f.read()
    else:
        template_content = ""
    
    # Конструиране на DATABASE_URL
    database_url = f"postgresql://{config['db_user']}:{config['db_password']}@{config['host']}:{config['port']}/{config['db_name']}"
    
    # Основни настройки за .env файла
    env_content = f"""# WebPortal Environment Configuration
# Generated by setup_database.py

# Flask Configuration
FLASK_ENV=development
DEBUG=True
TESTING=False

# Database Configuration
DATABASE_URL={database_url}

# Security Settings
SECRET_KEY=dev-secret-key-change-in-production
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=3600

# File Upload Settings
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/webportal.log

# Email Settings (Optional - configure if needed)
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ Environment file created/updated")
    return True

def setup_virtual_environment():
    """Проверява и създава виртуална среда ако не съществува"""
    print_step(5, "Setting up Python virtual environment")
    
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command("python3 -m venv venv", "Virtual environment created"):
            return False
    else:
        print("ℹ️  Virtual environment already exists")
    
    # Проверка дали може да се активира
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.exists():
        print("❌ Virtual environment seems corrupted, recreating...")
        run_command("rm -rf venv", "Removed old virtual environment")
        if not run_command("python3 -m venv venv", "Virtual environment recreated"):
            return False
    
    print("✅ Virtual environment is ready")
    return True

def install_dependencies():
    """Инсталира Python dependencies"""
    print_step(6, "Installing Python dependencies")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt file not found!")
        return False
    
    activate_and_install = """
    source venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
    """
    
    if not run_command(activate_and_install, "Dependencies installed"):
        print("❌ Failed to install dependencies!")
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def run_database_migrations(config):
    """Изпълнява database миграциите"""
    print_step(7, "Running database migrations")
    
    # Създаване на environment за Flask
    env = os.environ.copy()
    env['DATABASE_URL'] = f"postgresql://{config['db_user']}:{config['db_password']}@{config['host']}:{config['port']}/{config['db_name']}"
    env['FLASK_APP'] = 'webportal.py'
    
    migration_commands = [
        "source venv/bin/activate && flask db upgrade"
    ]
    
    for cmd in migration_commands:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Migration failed: {result.stderr}")
            return False
        
        if result.stdout:
            print(result.stdout)
    
    print("✅ Database migrations completed")
    return True

def create_admin_user(config):
    """Създава администратор потребител"""
    print_step(8, "Creating admin user")
    
    print("Enter admin user details:")
    admin_email = input("Admin email: ")
    admin_password = getpass.getpass("Admin password: ")
    admin_first_name = input("First name [Admin]: ") or "Admin"
    admin_last_name = input("Last name [User]: ") or "User"
    
    if not admin_email or not admin_password:
        print("❌ Email and password are required!")
        return False
    
    # Създаване на Python скрипт за създаване на admin потребителя
    create_admin_script = f'''
import sys
sys.path.append('.')

from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Проверка дали admin потребителят съществува
    admin = User.query.filter_by(email="{admin_email}").first()
    
    if admin:
        print("ℹ️  Admin user already exists, updating password...")
        admin.password_hash = generate_password_hash("{admin_password}")
    else:
        print("Creating new admin user...")
        admin = User(
            email="{admin_email}",
            password_hash=generate_password_hash("{admin_password}"),
            first_name="{admin_first_name}",
            last_name="{admin_last_name}",
            is_superuser=True,
            is_active=True,
            is_verified=True
        )
        db.session.add(admin)
    
    db.session.commit()
    print(f"✅ Admin user created/updated: {admin_email}")
'''
    
    # Записване и изпълняване на скрипта
    with open("temp_create_admin.py", "w") as f:
        f.write(create_admin_script)
    
    env = os.environ.copy()
    env['DATABASE_URL'] = f"postgresql://{config['db_user']}:{config['db_password']}@{config['host']}:{config['port']}/{config['db_name']}"
    
    result = subprocess.run(
        "source venv/bin/activate && python temp_create_admin.py",
        shell=True, env=env, capture_output=True, text=True
    )
    
    # Изтриване на временния файл
    os.remove("temp_create_admin.py")
    
    if result.returncode != 0:
        print(f"❌ Failed to create admin user: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def create_sample_data(config):
    """Създава примерни данни (опционално)"""
    print_step(9, "Creating sample data (optional)")
    
    create_sample = input("Do you want to create sample data? (y/N): ").lower().strip()
    
    if create_sample != 'y':
        print("ℹ️  Skipping sample data creation")
        return True
    
    sample_data_script = '''
import sys
sys.path.append('.')

from app import create_app, db
from app.models.building import Building
from app.models.finance import ExpenseCategory, AllocationMethodEnum

app = create_app()

with app.app_context():
    # Създаване на примерна сграда
    if not Building.query.first():
        building = Building(
            name="Примерна Сграда",
            address="бул. България 123",
            city="София",
            postal_code="1000",
            country="България",
            total_units=20,
            year_built=2000,
            description="Примерна жилищна сграда за демонстрация"
        )
        db.session.add(building)
        db.session.flush()  # За да получим ID-то
        
        # Създаване на основни категории разходи
        categories = [
            {
                'code': 'cleaning',
                'name': 'Почистване',
                'description': 'Почистване на общите части',
                'allocation_method': AllocationMethodEnum.PER_UNIT
            },
            {
                'code': 'elevator',
                'name': 'Асансьор',
                'description': 'Поддръжка и ремонт на асансьора',
                'allocation_method': AllocationMethodEnum.SHARES
            },
            {
                'code': 'electricity',
                'name': 'Електричество',
                'description': 'Електричество за общите части',
                'allocation_method': AllocationMethodEnum.METERED
            }
        ]
        
        for cat_data in categories:
            category = ExpenseCategory(
                building_id=building.id,
                code=cat_data['code'],
                name=cat_data['name'],
                description=cat_data['description'],
                allocation_method=cat_data['allocation_method'],
                is_active=True
            )
            db.session.add(category)
        
        db.session.commit()
        print("✅ Sample building and expense categories created")
    else:
        print("ℹ️  Sample data already exists")
'''
    
    with open("temp_sample_data.py", "w") as f:
        f.write(sample_data_script)
    
    env = os.environ.copy()
    env['DATABASE_URL'] = f"postgresql://{config['db_user']}:{config['db_password']}@{config['host']}:{config['port']}/{config['db_name']}"
    
    result = subprocess.run(
        "source venv/bin/activate && python temp_sample_data.py",
        shell=True, env=env, capture_output=True, text=True
    )
    
    os.remove("temp_sample_data.py")
    
    if result.returncode != 0:
        print(f"❌ Failed to create sample data: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def print_completion_info(config):
    """Показва информация за завършване"""
    print("\n" + "=" * 60)
    print("🎉 WebPortal Database Setup Completed Successfully!")
    print("=" * 60)
    
    print(f"\n📋 Setup Summary:")
    print(f"   • Database: {config['db_name']}")
    print(f"   • Database User: {config['db_user']}")
    print(f"   • Host: {config['host']}:{config['port']}")
    
    print(f"\n🚀 Next Steps:")
    print(f"   1. Start the application:")
    print(f"      source venv/bin/activate")
    print(f"      python run_debug.py")
    print(f"")
    print(f"   2. Access the application:")
    print(f"      Web interface: http://localhost:5001")
    print(f"      Admin panel: http://localhost:5001/admin")
    print(f"")
    print(f"   3. Login with your admin credentials")
    
    print(f"\n📚 Documentation:")
    print(f"   • README.md - Quick start guide")
    print(f"   • DEPLOYMENT.md - Production deployment")
    
    print(f"\n🔧 Configuration:")
    print(f"   • Environment file: .env")
    print(f"   • Logs directory: logs/")
    print(f"   • Uploads directory: uploads/")

def main():
    """Главна функция"""
    print_header()
    
    # Проверка дали сме в правилната директория
    if not Path("webportal.py").exists():
        print("❌ This script must be run from the WebPortal project root directory!")
        print("Make sure you're in the directory containing webportal.py")
        sys.exit(1)
    
    try:
        # Стъпка 1: Проверка на PostgreSQL
        if not check_postgresql():
            sys.exit(1)
        
        # Стъпка 2: Получаване на конфигурация
        config = get_database_config()
        if not config:
            sys.exit(1)
        
        # Стъпка 3: Създаване на база данни и потребител
        if not create_database_and_user(config):
            sys.exit(1)
        
        # Стъпка 4: Настройка на environment файл
        if not setup_environment_file(config):
            sys.exit(1)
        
        # Стъпка 5: Настройка на виртуална среда
        if not setup_virtual_environment():
            sys.exit(1)
        
        # Стъпка 6: Инсталация на dependencies
        if not install_dependencies():
            sys.exit(1)
        
        # Стъпка 7: Миграции на базата данни
        if not run_database_migrations(config):
            sys.exit(1)
        
        # Стъпка 8: Създаване на admin потребител
        if not create_admin_user(config):
            sys.exit(1)
        
        # Стъпка 9: Създаване на примерни данни (опционално)
        if not create_sample_data(config):
            sys.exit(1)
        
        # Завършване
        print_completion_info(config)
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()