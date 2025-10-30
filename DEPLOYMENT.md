# WebPortal - Production Deployment Guide

🚀 **Пълно ръководство за production deployment на WebPortal Flask приложението**

## 📋 Съдържание

- [Системни изисквания](#-системни-изисквания)
- [Подготовка на сървъра](#️-подготовка-на-сървъра)
- [Инсталация](#-инсталация)
- [База данни](#️-база-данни)
- [Nginx конфигурация](#-nginx-конфигурация)
- [SSL/TLS настройка](#-ssltls-настройка)
- [Systemd сервиз](#️-systemd-сервиз)
- [Мониторинг](#-мониторинг)
- [Backup стратегия](#-backup-стратегия)
- [Поддръжка](#️-поддръжка)

## 💻 Системни изисквания

### Минимални изисквания
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 2GB (препоръчително 4GB+)
- **Storage**: 20GB свободно място
- **CPU**: 2 cores (препоръчително 4+)
- **Network**: Стабилна интернет връзка

### Software зависимости
- Python 3.11+
- PostgreSQL 13+
- Nginx 1.18+
- Redis 6.0+ (опционално за caching)
- Git
- Supervisor или Systemd

## 🛠️ Подготовка на сървъра

### 1. Обновяване на системата

```bash
# Ubuntu/Debian
 apt update &&  apt upgrade -y

# CentOS/RHEL
 yum update -y
# или за newer versions
 dnf update -y
```

### 2. Инсталация на основни пакети

```bash
# Ubuntu/Debian
 apt install -y python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib nginx git curl \
    build-essential libpq-dev supervisor

# CentOS/RHEL
 dnf install -y python3.11 python3.11-devel \
    postgresql postgresql-server postgresql-contrib \
    nginx git curl gcc postgresql-devel supervisor
```

### 3. Създаване на потребител

```bash
# Създаване на системен потребител
 useradd -m -s /bin/bash webportal

# Създаване на директории
 mkdir -p /opt/webportal
 chown webportal:webportal /opt/webportal

# Преминаване към потребителя
 su - webportal
```

## 📦 Инсталация

### 1. Клониране на проекта

```bash
# Като webportal потребител
cd /opt
git clone <your-repository-url> webportal
cd webportal

# Checkout production branch
git checkout main
```

### 2. Виртуална среда и dependencies

```bash
# Създаване на виртуална среда
python3.11 -m venv venv
source venv/bin/activate

# Инсталация на production dependencies
pip install --upgrade pip
pip install -r requirements-prod.txt
```

### 3. Environment конфигурация

```bash
# Копиране на template
cp env.template .env

# Редактиране на production настройки
nano .env
```

Пример .env за production:

```bash
# Production конфигурация
FLASK_ENV=production
DEBUG=False
TESTING=False

# Secret key - генерирайте силен ключ!
SECRET_KEY=your-super-secure-secret-key-change-this

# База данни
DATABASE_URL=postgresql://webportal_user:secure_password@localhost/webportal

# Security настройки
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600

# Upload настройки
UPLOAD_FOLDER=/opt/webportal/uploads
MAX_CONTENT_LENGTH=16777216

# Email настройки (ако се използва)
MAIL_SERVER=smtp.yourdomain.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=noreply@yourdomain.com
MAIL_PASSWORD=your-mail-password

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/webportal/logs/webportal.log
```

### 4. Създаване на директории

```bash
# Като webportal потребител
mkdir -p logs uploads static/uploads
chmod 755 logs uploads static/uploads
```

## 🗄️ База данни

### 1. PostgreSQL настройка

```bash
# Като root потребител
 systemctl enable postgresql
 systemctl start postgresql

# Създаване на потребител и база данни
 -u postgres psql << EOF
CREATE USER webportal_user WITH PASSWORD 'secure_password_change_this';
CREATE DATABASE webportal OWNER webportal_user;
GRANT ALL PRIVILEGES ON DATABASE webportal TO webportal_user;
ALTER USER webportal_user CREATEDB;
\q
EOF
```

### 2. Конфигурация на PostgreSQL

```bash
# Редактиране на pg_hba.conf
 nano /etc/postgresql/13/main/pg_hba.conf

# Добавете реда:
# local   webportal    webportal_user                     md5
```

### 3. Миграции и начални данни

```bash
# Като webportal потребител
cd /opt/webportal
source venv/bin/activate

# Стартиране на миграциите
flask db upgrade

# Създаване на администратор
python scripts/create_admin.py

# За персонализиран администратор (препоръчително за production)
python scripts/create_admin.py --custom

# Default администратор (само за тестване):
# Email: admin@webportal.local
# Password: admin123
# ⚠️ ВАЖНО: Сменете паролата веднага след инсталация!
```

## 🌐 Nginx конфигурация

### 1. Основна конфигурация

```bash
# Създаване на конфигурационен файл
 nano /etc/nginx/sites-available/webportal
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Временно пренасочване към HTTPS (ще се конфигурира по-късно)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL конфигурация (ще се добави по-късно)
    # ssl_certificate /path/to/certificate.crt;
    # ssl_certificate_key /path/to/private.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Logging
    access_log /var/log/nginx/webportal_access.log;
    error_log /var/log/nginx/webportal_error.log;

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static {
        alias /opt/webportal/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Gzip compression
        gzip on;
        gzip_types text/css application/javascript image/svg+xml;
    }

    # Upload files
    location /uploads {
        alias /opt/webportal/uploads;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Активиране на сайта

```bash
# Активиране на конфигурацията
 ln -s /etc/nginx/sites-available/webportal /etc/nginx/sites-enabled/

# Тестване на конфигурацията
 nginx -t

# Рестартиране на Nginx
 systemctl reload nginx
```

## 🔒 SSL/TLS настройка

### Опция 1: Let's Encrypt (препоръчително)

```bash
# Инсталация на Certbot
 apt install certbot python3-certbot-nginx

# Получаване на SSL сертификат
 certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Автоматично обновяване
 crontab -e
# Добавете: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Опция 2: Собствен сертификат

```bash
# Генериране на самоподписан сертификат (за тестване)
 openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/webportal.key \
    -out /etc/ssl/certs/webportal.crt

# Обновяване на Nginx конфигурацията
# ssl_certificate /etc/ssl/certs/webportal.crt;
# ssl_certificate_key /etc/ssl/private/webportal.key;
```

## ⚙️ Systemd сервиз

### 1. Gunicorn конфигурация

```bash
# Редактиране на gunicorn.conf.py
nano /opt/webportal/gunicorn.conf.py
```

```python
# Gunicorn production конфигурация
bind = "127.0.0.1:8000"
workers = 4  # 2 * CPU cores
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 60
keepalive = 5
user = "webportal"
group = "webportal"
tmp_upload_dir = None
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}

# Logging
accesslog = "/opt/webportal/logs/gunicorn_access.log"
errorlog = "/opt/webportal/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "webportal"

# Restart workers gracefully
graceful_timeout = 30
```

### 2. Systemd service файл

```bash
# Създаване на service файл
 nano /etc/systemd/system/webportal.service
```

```ini
[Unit]
Description=Gunicorn instance to serve WebPortal
After=network.target postgresql.service

[Service]
User=webportal
Group=webportal
WorkingDirectory=/opt/webportal
Environment="PATH=/opt/webportal/venv/bin"
ExecStart=/opt/webportal/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/webportal/logs /opt/webportal/uploads
ProtectHome=true
PrivateDevices=true

[Install]
WantedBy=multi-user.target
```

### 3. Стартиране на сервиза

```bash
# Зареждане на новия service
 systemctl daemon-reload

# Активиране на сервиза
 systemctl enable webportal

# Стартиране
 systemctl start webportal

# Проверка на статуса
 systemctl status webportal

# Преглед на логове
 journalctl -u webportal -f
```

## 📊 Мониторинг

### 1. Log ротация

```bash
# Създаване на logrotate конфигурация
 nano /etc/logrotate.d/webportal
```

```
/opt/webportal/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 webportal webportal
    postrotate
        systemctl reload webportal
    endscript
}
```

### 2. Основен мониторинг

```bash
# Проверка на услугите
 systemctl status webportal nginx postgresql

# Проверка на портове
ss -tulpn | grep -E ':(80|443|8000|5432)'

# Проверка на дисковото пространство
df -h

# Проверка на паметта
free -m

# Проверка на процесите
ps aux | grep -E '(gunicorn|nginx|postgres)'
```

### 3. Health check скрипт

```bash
# Създаване на health check скрипт
nano /opt/webportal/scripts/health_check.sh
```

```bash
#!/bin/bash

# Health check скрипт за WebPortal
LOG_FILE="/opt/webportal/logs/health_check.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Проверка на web сървъра
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "[$DATE] Web server: OK" >> $LOG_FILE
else
    echo "[$DATE] Web server: FAIL" >> $LOG_FILE
    systemctl restart webportal
fi

# Проверка на базата данни
if pg_isready -h localhost -p 5432 -U webportal_user > /dev/null; then
    echo "[$DATE] Database: OK" >> $LOG_FILE
else
    echo "[$DATE] Database: FAIL" >> $LOG_FILE
fi

# Проверка на дисковото пространство
DISK_USAGE=$(df /opt | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "[$DATE] Disk space warning: ${DISK_USAGE}%" >> $LOG_FILE
fi
```

```bash
# Правене на executable
chmod +x /opt/webportal/scripts/health_check.sh

# Добавяне в crontab
crontab -e
# */5 * * * * /opt/webportal/scripts/health_check.sh
```

## 💾 Backup стратегия

### 1. Database backup

```bash
# Създаване на backup скрипт
nano /opt/webportal/scripts/backup_db.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/opt/webportal/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="webportal_home"
DB_USER="webportal_user"

# Създаване на backup директория
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Запазване само на последните 30 backup-а
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: db_backup_$DATE.sql.gz"
```

### 2. Files backup

```bash
# Backup на важни файлове
tar -czf /opt/webportal/backups/files_backup_$(date +%Y%m%d).tar.gz \
    /opt/webportal/uploads \
    /opt/webportal/.env \
    /opt/webportal/logs
```

### 3. Automated backup

```bash
# Добавяне в crontab
crontab -e

# Ежедневен backup в 2:00 AM
0 2 * * * /opt/webportal/scripts/backup_db.sh

# Седмичен файлов backup в неделя в 3:00 AM  
0 3 * * 0 tar -czf /opt/webportal/backups/files_backup_$(date +%Y%m%d).tar.gz /opt/webportal/uploads /opt/webportal/.env
```

## 🔧 Поддръжка

### Обновяване на приложението

```bash
# Като webportal потребител
cd /opt/webportal

# Backup преди обновяване
git stash
./scripts/backup_db.sh

# Pull на новия код
git pull origin main

# Обновяване на dependencies
source venv/bin/activate
pip install -r requirements-prod.txt

# Миграции на базата данни
flask db upgrade

# Рестартиране на сервиза
 systemctl restart webportal
```

### Log анализ

```bash
# Най-често срещани грешки
tail -1000 /opt/webportal/logs/webportal.log | grep ERROR

# Nginx access log статистика
tail -1000 /var/log/nginx/webportal_access.log | awk '{print $9}' | sort | uniq -c | sort -nr

# Gunicorn performance
tail -1000 /opt/webportal/logs/gunicorn_access.log | awk '{print $10}' | sort -n | tail -10
```

### Performance тюнинг

```bash
# PostgreSQL оптимизация
 nano /etc/postgresql/13/main/postgresql.conf

# Примерни настройки за 4GB RAM сървър:
# shared_buffers = 1GB
# effective_cache_size = 3GB
# maintenance_work_mem = 256MB
# work_mem = 4MB
```

### Отстраняване на неизправности

**Проблем**: 502 Bad Gateway
```bash
# Проверка на Gunicorn
 systemctl status webportal
 journalctl -u webportal -n 50
```

**Проблем**: Бавна производителност
```bash
# Проверка на системните ресурси
htop
iotop
```

**Проблем**: Database връзка се отказва
```bash
# Проверка на PostgreSQL
 systemctl status postgresql
 -u postgres psql -c "SELECT version();"
```

---

## 🏁 Финален checklist

- [ ] Сървърът е обновен и защитен
- [ ] PostgreSQL е инсталиран и конфигуриран
- [ ] Приложението е клонирано и настроено
- [ ] Database миграциите са изпълнени
- [ ] Admin потребител е създаден (admin@webportal.local / admin123)
- [ ] Default паролата е сменена с по-сигурна
- [ ] Nginx е конфигуриран правилно
- [ ] SSL сертификатът е инсталиран
- [ ] Systemd service е активиран
- [ ] Backup стратегията е настроена
- [ ] Мониторингът работи
- [ ] Health check-овете са конфигурирани
- [ ] Логовете се ротират правилно
- [ ] Firewall правилата са настроени

🎉 **Congratulations! WebPortal е готов за production!**