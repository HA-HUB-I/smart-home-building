# WebPortal - Система за Управление на Жилищни Сгради

🏢 **Мощна Flask web платформа за управление на апартаментни сгради, етажна собственост и общински дейности.**

## ⚡ Quick Start

```bash
# 1. Клониране на проекта
git clone https://github.com/HA-HUB-I/smart-home-building.git webportal
cd webportal

# 2. Инсталация на dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Конфигурация
cp env.template .env
# Редактирайте .env файла с вашите настройки

# 4. Бързо инициализиране
./scripts/quick_setup.sh

# 5. Стартиране
python run_debug.py
```

🌐 **Отворете браузър на http://localhost:5001**

🔐 **Default администратор:**
- Email: `admin@webportal.local`
- Password: `admin123`

## 📋 Съдържание

- [Функционалности](#-функционалности)
- [Технологии](#️-технологии)
- [Бърз старт](#-бърз-старт)
- [Инсталация](#-инсталация)
- [Конфигурация](#️-конфигурация)
- [База данни](#️-база-данни)
- [Разработка](#-разработка)
- [Production Deploy](#-production-deploy)
- [API Документация](#-api-документация)
- [Поддръжка](#-поддръжка)

## 🚀 Функционалности

### 🏠 **Управление на Сгради**
- Регистрация и управление на многоетажни сгради
- Детайли за апартаменти и общи части
- Геолокация и адресни данни
- История на промени

### 💰 **Финансово Управление**
- Категории разходи с различни методи на разпределение
- Автоматично генериране на такси и фактури
- Плащания и финансови отчети
- Управление на месечни такси и ремонтни фондове

### 👥 **Управление на Потребители**
- Многостепенна система за роли и права
- Собственици, наематели, управители
- Профили и настройки на потребителите

### 📢 **Комуникация**
- Съобщения и известия
- Гласуване и решения
- Документооборот

### 🔧 **Разширения**
- API интеграции с външни системи
- Плъгини и персонализирани полета
- Webhook уведомления

### 🛡️ **Администрация**
- Flask-Admin интерфейс
- Одит лог и проследяване на действията
- Системни настройки

## ⚙️ Технологии

- **Backend**: Python 3.11+, Flask 2.3+
- **База данни**: PostgreSQL 13+
- **ORM**: SQLAlchemy 2.0+
- **Миграции**: Alembic
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Автентификация**: Flask-Login
- **Администрация**: Flask-Admin
- **WSGI Server**: Gunicorn
- **Проследяване**: Система за логове

## 🏃 Бърз старт

### Предварителни изисквания
- Python 3.11 или по-нова версия
- PostgreSQL 13+
- Git

### 1. Клониране на проекта
```bash
git clone <repository-url> webportal
cd webportal

# За development работа
git checkout dev
```

### 2. Създаване на виртуална среда
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

### 3. Инсталация на dependencies
```bash
pip install -r requirements.txt
```

### 4. Настройка на базата данни
```bash
# Създаване на база данни
 -u postgres createdb webportal_dev

# Копиране на конфигурацията
cp env.template .env
# Редактирайте .env файла с вашите настройки
```

### 5. Инициализация на базата данни
```bash
# Стартиране на миграциите
flask db upgrade

# Създаване на администратор
python scripts/create_admin.py

# За персонализиран администратор
python scripts/create_admin.py --custom
```

### 6. Стартиране на приложението
```bash
# Development режим
python run_debug.py

# Production режим
python webportal.py
```

### 7. Достъп до приложението
- **Web интерфейс**: http://localhost:5001
- **Admin панел**: http://localhost:5001/admin

### 8. Default администратор
```
📧 Email: admin@webportal.local
🔑 Password: admin123
🔐 Role: Superuser
```
⚠️ **ВАЖНО**: Сменете паролата след първото влизане!

## 📦 Инсталация

### Development Setup

```bash
# 1. Клониране
git clone <repository-url> webportal
cd webportal
git checkout dev

# 2. Виртуална среда
python3 -m venv venv
source venv/bin/activate

# 3. Development dependencies
pip install -r requirements.txt

# 4. Environment файл
cp env.template .env
```

### Production Setup

```bash
# 1. Клониране
git clone <repository-url> webportal
cd webportal
git checkout main

# 2. Виртуална среда
python3 -m venv venv
source venv/bin/activate

# 3. Production dependencies
pip install -r requirements-prod.txt

# 4. Environment файл
cp env.template .env
# Редактирайте .env с production стойности
```

## ⚙️ Конфигурация

### Environment Variables (.env)

```bash
# База данни
DATABASE_URL=postgresql://user:password@localhost/webportal_dev
DATABASE_URL_PROD=postgresql://user:password@localhost/webportal

# Flask настройки
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=development  # development/production
DEBUG=True  # False за production

# Email настройки (опционално)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security настройки
SESSION_COOKIE_SECURE=False  # True за HTTPS
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=3600

# Upload директории
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Конфигуриране на PostgreSQL

```sql
-- Създаване на потребител
CREATE USER webportal_user WITH PASSWORD 'strong_password';

-- Създаване на development база
CREATE DATABASE webportal_dev OWNER webportal_user;

-- Създаване на production база
CREATE DATABASE webportal OWNER webportal_user;

-- Даване на права
GRANT ALL PRIVILEGES ON DATABASE webportal_dev TO webportal_user;
GRANT ALL PRIVILEGES ON DATABASE webportal TO webportal_user;
```

## 🗄️ База данни

### Миграции

```bash
# Инициализиране на миграции (ако не е направено)
flask db init

# Създаване на нова миграция
flask db migrate -m "Описание на промяната"

# Прилагане на миграциите
flask db upgrade

# Връщане назад
flask db downgrade

# История на миграциите
flask db history
```

### Автоматично създаване на база данни

Използвайте предоставения скрипт:

```bash
./scripts/setup_database.py
```

### Backup и Restore

```bash
# Backup
pg_dump -U webportal_user -h localhost webportal > backup.sql

# Restore
psql -U webportal_user -h localhost webportal < backup.sql
```

## 💻 Разработка

### Структура на проекта

```
webportal/
├── app/                    # Основно Flask приложение
│   ├── admin/             # Flask-Admin views
│   ├── auth/              # Автентификация и упълномощаване
│   ├── buildings/         # Управление на сгради
│   ├── communications/    # Съобщения и известия
│   ├── extensions/        # Разширения и интеграции
│   ├── finance/          # Финансово управление
│   ├── main/             # Главни страници
│   ├── models/           # SQLAlchemy модели
│   ├── templates/        # Jinja2 templates
│   └── users/            # Управление на потребители
├── migrations/           # Alembic миграции
├── static/              # Статични файлове (CSS, JS, изображения)
├── tests/               # Unit тестове
├── config.py           # Конфигурация на приложението
├── requirements.txt    # Python dependencies
└── wsgi.py            # WSGI entry point
```

### Стилове на код

```bash
# Форматиране с black
black app/ tests/

# Проверка с flake8
flake8 app/ tests/

# Type checking с mypy
mypy app/
```

### Тестване

```bash
# Всички тестове
python -m pytest

# С coverage
python -m pytest --cov=app

# Конкретен тест
python -m pytest tests/test_auth.py::TestLogin::test_valid_login
```

### Git работен процес

```bash
# Работа се извършва в dev бранча
git checkout dev

# Създаване на feature branch
git checkout -b feature/new-feature

# Commit промени
git add .
git commit -m "Add new feature"

# Merge обратно в dev
git checkout dev
git merge feature/new-feature

# За production release
git checkout main
git merge dev
git tag v1.0.0
```

## 🚀 Production Deploy

### С Gunicorn

```bash
# Инсталиране на production зависимости
pip install -r requirements-prod.txt

# Стартиране с Gunicorn
gunicorn --config gunicorn.conf.py wsgi:app

# Със systemd service
 cp gunicorn.service /etc/systemd/system/
 systemctl enable gunicorn
 systemctl start gunicorn
```

### Nginx конфигурация

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/webportal/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker Deploy

```bash
# Използвайте предоставените файлове
docker-compose up -d
```

### Използване на deploy скриптовете

```bash
# Обикновен deploy
./deploy.sh

# Secure deploy с SSL
./secure_deploy.sh
```

## 📚 API Документация

WebPortal предоставя REST API за интеграция с външни системи.

### Автентификация

```bash
# Login
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Използване на токен
curl -H "Authorization: Bearer <token>" \
  http://localhost:5001/api/buildings
```

### Основни endpoints

- `GET /api/buildings` - Списък сгради
- `GET /api/buildings/{id}` - Детайли за сграда
- `GET /api/finance/categories` - Финансови категории
- `POST /api/finance/expenses` - Създаване на разход
- `GET /api/users` - Списък потребители

### API документация

Пълната API документация е достъпна на:
- http://localhost:5001/api/docs (Swagger UI)

## 🛠️ Поддръжка

### Логове

```bash
# Преглед на логове
tail -f logs/webportal.log

# Конфигуриране на log levels в config.py
```

### Backup стратегия

1. **База данни**: Ежедневни pg_dump backups
2. **Файлове**: Backup на uploads директорията
3. **Конфигурация**: Backup на .env файлове

### Мониторинг

- Проследяване на памет и CPU usage
- Database performance мониторинг
- Error rate tracking
- Uptime мониторинг

### Често срещани проблеми

**Проблем**: База данни връзка се отказва
**Решение**: Проверете PostgreSQL service и DATABASE_URL

**Проблем**: Static файлове не се зареждат
**Решение**: Проверете permissions на static директорията

**Проблем**: 500 Internal Server Error
**Решение**: Проверете логовете в logs/webportal.log

### Контакти за поддръжка

- 🐛 **Bugs**: Отворете issue в GitHub repository
- 📧 **Email**: support@unlck.app
- 📱 **Telegram**: [HA_HUB_I](https://t.me/HA_HUB_I)
- 📚 **Документация**: Вижте wiki страниците

---

## 📝 Лиценз

Този проект е лицензиран под MIT License - вижте [LICENSE](LICENSE) файла за детайли.

## 🤝 Принос

Приветстваме приноси! Моля, прочетете [CONTRIBUTING.md](CONTRIBUTING.md) за детайли относно нашия код на поведение и процеса за изпращане на pull request-и.

---

**WebPortal** - Направено с ❤️ за българските жилищни сгради