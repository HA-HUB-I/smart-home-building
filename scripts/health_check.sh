#!/bin/bash

# WebPortal Health Check Script
# Проверява състоянието на всички компоненти

LOG_FILE="logs/health_check.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Цветове за output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция за логване
log_message() {
    echo "[$DATE] $1" >> $LOG_FILE
    echo -e "$1"
}

# Проверка на web сървъра
check_web_server() {
    echo -n "🌐 Web Server: "
    if curl -f -s http://localhost:5001/health > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        log_message "Web server: OK"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        log_message "Web server: FAIL"
        return 1
    fi
}

# Проверка на базата данни
check_database() {
    echo -n "🗄️  Database: "
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        log_message "Database: OK"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        log_message "Database: FAIL"
        return 1
    fi
}

# Проверка на дисковото пространство
check_disk_space() {
    echo -n "💾 Disk Space: "
    DISK_USAGE=$(df /opt | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $DISK_USAGE -lt 80 ]; then
        echo -e "${GREEN}OK (${DISK_USAGE}%)${NC}"
        log_message "Disk space: OK (${DISK_USAGE}%)"
        return 0
    elif [ $DISK_USAGE -lt 90 ]; then
        echo -e "${YELLOW}WARNING (${DISK_USAGE}%)${NC}"
        log_message "Disk space: WARNING (${DISK_USAGE}%)"
        return 1
    else
        echo -e "${RED}CRITICAL (${DISK_USAGE}%)${NC}"
        log_message "Disk space: CRITICAL (${DISK_USAGE}%)"
        return 2
    fi
}

# Проверка на паметта
check_memory() {
    echo -n "🧠 Memory: "
    MEM_USAGE=$(free | awk 'FNR==2{printf "%.0f", $3/($3+$4)*100}')
    
    if [ $MEM_USAGE -lt 80 ]; then
        echo -e "${GREEN}OK (${MEM_USAGE}%)${NC}"
        log_message "Memory: OK (${MEM_USAGE}%)"
        return 0
    elif [ $MEM_USAGE -lt 90 ]; then
        echo -e "${YELLOW}WARNING (${MEM_USAGE}%)${NC}"
        log_message "Memory: WARNING (${MEM_USAGE}%)"
        return 1
    else
        echo -e "${RED}CRITICAL (${MEM_USAGE}%)${NC}"
        log_message "Memory: CRITICAL (${MEM_USAGE}%)"
        return 2
    fi
}

# Проверка на процесите
check_processes() {
    echo -n "⚙️  Processes: "
    
    # Проверка на Gunicorn процеси
    GUNICORN_COUNT=$(pgrep -f "gunicorn.*webportal" | wc -l)
    
    if [ $GUNICORN_COUNT -gt 0 ]; then
        echo -e "${GREEN}OK (${GUNICORN_COUNT} workers)${NC}"
        log_message "Processes: OK (${GUNICORN_COUNT} workers)"
        return 0
    else
        echo -e "${RED}FAIL (No workers running)${NC}"
        log_message "Processes: FAIL (No workers running)"
        return 1
    fi
}

# Проверка на логовете за грешки
check_logs() {
    echo -n "📋 Recent Errors: "
    
    ERROR_COUNT=0
    if [ -f "logs/webportal.log" ]; then
        ERROR_COUNT=$(tail -100 logs/webportal.log | grep -c "ERROR" 2>/dev/null || echo 0)
    fi
    
    if [ $ERROR_COUNT -eq 0 ]; then
        echo -e "${GREEN}OK (No recent errors)${NC}"
        log_message "Recent errors: OK (No recent errors)"
        return 0
    elif [ $ERROR_COUNT -lt 5 ]; then
        echo -e "${YELLOW}WARNING (${ERROR_COUNT} errors)${NC}"
        log_message "Recent errors: WARNING (${ERROR_COUNT} errors)"
        return 1
    else
        echo -e "${RED}CRITICAL (${ERROR_COUNT} errors)${NC}"
        log_message "Recent errors: CRITICAL (${ERROR_COUNT} errors)"
        return 2
    fi
}

# Главна функция
main() {
    echo "🔍 WebPortal Health Check - $(date)"
    echo "=" * 40
    
    TOTAL_CHECKS=6
    FAILED_CHECKS=0
    WARNING_CHECKS=0
    
    # Изпълнение на всички проверки
    check_web_server || ((FAILED_CHECKS++))
    check_database || ((FAILED_CHECKS++))
    
    check_disk_space
    case $? in
        1) ((WARNING_CHECKS++)) ;;
        2) ((FAILED_CHECKS++)) ;;
    esac
    
    check_memory
    case $? in
        1) ((WARNING_CHECKS++)) ;;
        2) ((FAILED_CHECKS++)) ;;
    esac
    
    check_processes || ((FAILED_CHECKS++))
    
    check_logs
    case $? in
        1) ((WARNING_CHECKS++)) ;;
        2) ((FAILED_CHECKS++)) ;;
    esac
    
    echo
    echo "📊 Summary:"
    echo "   ✅ Passed: $((TOTAL_CHECKS - FAILED_CHECKS - WARNING_CHECKS))"
    echo "   ⚠️  Warnings: $WARNING_CHECKS"
    echo "   ❌ Failed: $FAILED_CHECKS"
    
    # Общо състояние
    if [ $FAILED_CHECKS -eq 0 ] && [ $WARNING_CHECKS -eq 0 ]; then
        echo -e "\n🟢 Overall Status: ${GREEN}HEALTHY${NC}"
        exit 0
    elif [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "\n🟡 Overall Status: ${YELLOW}WARNING${NC}"
        exit 1
    else
        echo -e "\n🔴 Overall Status: ${RED}CRITICAL${NC}"
        exit 2
    fi
}

# Създаване на logs директория ако не съществува
mkdir -p logs

# Изпълнение на проверката
main "$@"