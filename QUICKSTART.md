# WebPortal - Кратко ръководство за клиенти

🚀 **Бърз старт за използване на WebPortal систeмата**

## 📥 Клониране на проекта

```bash
# Клонирайте хранилището
git clone /opt/webportal-flask webportal
cd webportal

# За development работa
git checkout dev

# За production deployment  
git checkout main
```

## ⚡ Автоматична инсталация

```bash
# Изпълнете автоматичния setup скрипт
python3 scripts/setup_database.py
```

Скриптът ще ви попита за:
- Database конфигурация
- Admin потребител данни
- Дали искате примерни данни

## 🏃 Бърз старт (Manual)

### 1. Виртуална среда
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. База данни 
```bash
# Копирайте конфигурацията
cp env.template .env
# Редактирайте .env с вашите настройки

# Стартирайте миграциите
flask db upgrade
```

### 3. Стартиране
```bash
# Development
python run_debug.py

# Production
python webportal.py
```

## 🌐 Достъп

- **Web интерфейс**: http://localhost:5001
- **Admin панел**: http://localhost:5001/admin

## 📚 Документация

- `README.md` - Подробно ръководство
- `DEPLOYMENT.md` - Production deployment
- `CONTRIBUTING.md` - За разработчици

## 🛠️ Полезни команди

```bash
# Health check
./scripts/health_check.sh

# Backup
./scripts/backup.sh

# Проверка на логове
tail -f logs/webportal.log
```

## 🆘 Поддръжка

Ако имате проблеми:
1. Проверете `logs/webportal.log`
2. Изпълнете `./scripts/health_check.sh`
3. Прегледайте документацията
4. Отворете issue в проекта