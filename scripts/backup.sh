#!/bin/bash

# WebPortal Backup Script
# Прави пълен backup на базата данни и важни файлове

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Цветове
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Конфигурация
DB_NAME="webportal"
DB_USER="webportal_user"
RETENTION_DAYS=30

# Функция за логване
log() {
    echo -e "[$DATE] $1"
}

# Създаване на backup директория
mkdir -p "$BACKUP_DIR"

log "${GREEN}🗄️  Starting WebPortal Backup${NC}"
log "Backup directory: $BACKUP_DIR"

# Database backup
log "${YELLOW}📊 Backing up database...${NC}"
DB_BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql.gz"

if pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$DB_BACKUP_FILE"; then
    DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
    log "${GREEN}✅ Database backup completed: $DB_SIZE${NC}"
else
    log "${RED}❌ Database backup failed!${NC}"
    exit 1
fi

# Files backup
log "${YELLOW}📁 Backing up files...${NC}"
FILES_BACKUP_FILE="$BACKUP_DIR/files_backup_$DATE.tar.gz"

tar -czf "$FILES_BACKUP_FILE" \
    -C "$PROJECT_DIR" \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="backups" \
    --exclude="logs/*.log" \
    uploads \
    .env \
    static/uploads 2>/dev/null

if [ $? -eq 0 ]; then
    FILES_SIZE=$(du -h "$FILES_BACKUP_FILE" | cut -f1)
    log "${GREEN}✅ Files backup completed: $FILES_SIZE${NC}"
else
    log "${RED}❌ Files backup failed!${NC}"
    exit 1
fi

# Configuration backup
log "${YELLOW}⚙️  Backing up configuration...${NC}"
CONFIG_BACKUP_FILE="$BACKUP_DIR/config_backup_$DATE.tar.gz"

tar -czf "$CONFIG_BACKUP_FILE" \
    -C "$PROJECT_DIR" \
    .env \
    config.py \
    gunicorn.conf.py \
    requirements*.txt 2>/dev/null

if [ $? -eq 0 ]; then
    CONFIG_SIZE=$(du -h "$CONFIG_BACKUP_FILE" | cut -f1)
    log "${GREEN}✅ Configuration backup completed: $CONFIG_SIZE${NC}"
else
    log "${RED}❌ Configuration backup failed!${NC}"
fi

# Cleanup old backups
log "${YELLOW}🧹 Cleaning up old backups...${NC}"
DELETED_COUNT=0

# Database backups
for file in "$BACKUP_DIR"/db_backup_*.sql.gz; do
    if [ -f "$file" ] && [ "$(find "$file" -mtime +$RETENTION_DAYS)" ]; then
        rm "$file"
        ((DELETED_COUNT++))
    fi
done

# Files backups
for file in "$BACKUP_DIR"/files_backup_*.tar.gz; do
    if [ -f "$file" ] && [ "$(find "$file" -mtime +$RETENTION_DAYS)" ]; then
        rm "$file"
        ((DELETED_COUNT++))
    fi
done

# Config backups
for file in "$BACKUP_DIR"/config_backup_*.tar.gz; do
    if [ -f "$file" ] && [ "$(find "$file" -mtime +$RETENTION_DAYS)" ]; then
        rm "$file"
        ((DELETED_COUNT++))
    fi
done

if [ $DELETED_COUNT -gt 0 ]; then
    log "${GREEN}✅ Cleaned up $DELETED_COUNT old backup files${NC}"
else
    log "${GREEN}ℹ️  No old backups to clean up${NC}"
fi

# Backup summary
log "${GREEN}📋 Backup Summary:${NC}"
log "   Database: $DB_BACKUP_FILE ($DB_SIZE)"
log "   Files: $FILES_BACKUP_FILE ($FILES_SIZE)"
log "   Config: $CONFIG_BACKUP_FILE ($CONFIG_SIZE)"

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "   Total backup size: $TOTAL_SIZE"

log "${GREEN}🎉 Backup completed successfully!${NC}"