#!/bin/bash
# WebPortal Production Deployment Script
# Автоматизира deployment на WebPortal с .env конфигурация

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WEBPORTAL_DIR="/opt/webportal-flask"
BACKUP_DIR="/opt/webportal-flask/backups"
LOG_FILE="/var/log/webportal/deployment.log"
VENV_DIR="$WEBPORTAL_DIR/venv"

# Ensure we're running from the correct directory
cd "$WEBPORTAL_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should NOT be run as root for security reasons!"
        print_status "Run as the webportal user instead: sudo -u webportal $0"
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "/var/log/webportal"
        "$BACKUP_DIR"
        "$WEBPORTAL_DIR/uploads"
        "$WEBPORTAL_DIR/static/uploads"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            sudo mkdir -p "$dir"
            sudo chown $(whoami):$(whoami) "$dir"
            print_success "Created directory: $dir"
        fi
    done
}

# Function to check .env file
check_env_file() {
    print_status "Checking .env configuration..."
    
    if [[ ! -f "$WEBPORTAL_DIR/.env" ]]; then
        print_error ".env file not found!"
        print_status "Copy .env.example to .env and configure it:"
        print_status "cp $WEBPORTAL_DIR/.env.example $WEBPORTAL_DIR/.env"
        print_status "nano $WEBPORTAL_DIR/.env"
        exit 1
    fi
    
    # Check for default values that need to be changed
    if grep -q "your-super-secret-flask-key-change-this-in-production" "$WEBPORTAL_DIR/.env"; then
        print_error "SECRET_KEY in .env is still using example value!"
        print_status "Run: python3 $WEBPORTAL_DIR/generate_secret_key.py"
        exit 1
    fi
    
    if grep -q "your-secure-db-password" "$WEBPORTAL_DIR/.env"; then
        print_warning "Database password in .env appears to be using example value"
    fi
    
    print_success ".env file exists and basic checks passed"
}

# Function to setup Python virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [[ ! -d "$VENV_DIR" ]]; then
        print_status "Creating new virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [[ -f "$WEBPORTAL_DIR/requirements.txt" ]]; then
        print_status "Installing Python packages..."
        pip install -r "$WEBPORTAL_DIR/requirements.txt"
        print_success "Python packages installed"
    else
        print_warning "requirements.txt not found - installing basic packages"
        pip install flask python-dotenv PyMySQL redis requests
    fi
}

# Function to validate environment
validate_environment() {
    print_status "Validating environment configuration..."
    
    source "$VENV_DIR/bin/activate"
    
    if python3 "$WEBPORTAL_DIR/validate_environment.py"; then
        print_success "Environment validation passed"
    else
        print_error "Environment validation failed!"
        print_status "Please fix the issues above before continuing deployment"
        exit 1
    fi
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    source "$VENV_DIR/bin/activate"
    
    if python3 "$WEBPORTAL_DIR/backend/database_manager.py"; then
        print_success "Database setup completed"
    else
        print_error "Database setup failed!"
        exit 1
    fi
}

# Function to backup existing installation
backup_existing() {
    if [[ -f "$WEBPORTAL_DIR/backend/app.py" ]]; then
        print_status "Creating backup of existing installation..."
        
        backup_name="webportal_backup_$(date +%Y%m%d_%H%M%S)"
        backup_path="$BACKUP_DIR/$backup_name.tar.gz"
        
        # Create backup excluding sensitive files and cache
        tar -czf "$backup_path" \
            --exclude="venv" \
            --exclude="__pycache__" \
            --exclude="*.pyc" \
            --exclude=".env" \
            --exclude="*.log" \
            --exclude="uploads" \
            -C "$WEBPORTAL_DIR" .
        
        print_success "Backup created: $backup_path"
    fi
}

# Function to update file permissions
set_permissions() {
    print_status "Setting file permissions..."
    
    # Make scripts executable
    chmod +x "$WEBPORTAL_DIR/generate_secret_key.py"
    chmod +x "$WEBPORTAL_DIR/validate_environment.py"
    chmod +x "$WEBPORTAL_DIR/backend/database_manager.py"
    
    # Secure .env file
    chmod 600 "$WEBPORTAL_DIR/.env"
    
    # Set proper permissions for web files
    find "$WEBPORTAL_DIR/backend/static" -type f -exec chmod 644 {} \;
    find "$WEBPORTAL_DIR/backend/templates" -type f -exec chmod 644 {} \;
    
    # Set permissions for log directory
    sudo chown -R $(whoami):www-data /var/log/webportal
    sudo chmod -R 775 /var/log/webportal
    
    print_success "File permissions set"
}

# Function to configure systemd service
setup_systemd_service() {
    print_status "Configuring systemd service..."
    
    # Create systemd service file
    cat > /tmp/webportal.service << EOF
[Unit]
Description=WebPortal Flask Application
After=network.target postgresql.service

[Service]
Type=exec
User=$(whoami)
Group=www-data
WorkingDirectory=$WEBPORTAL_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/python backend/app.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=3
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$WEBPORTAL_DIR /var/log/webportal /tmp

[Install]
WantedBy=multi-user.target
EOF

    # Install service file
    sudo mv /tmp/webportal.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable webportal
    
    print_success "Systemd service configured"
}

# Function to configure nginx
setup_nginx() {
    print_status "Configuring nginx..."
    
    # Check if nginx config already exists
    if [[ -f "$WEBPORTAL_DIR/nginx.conf" ]]; then
        print_status "Using existing nginx configuration"
    else
        print_warning "nginx.conf not found - please configure nginx manually"
        return
    fi
    
    # Copy nginx config if it doesn't exist in nginx sites
    if [[ ! -f "/etc/nginx/sites-available/webportal" ]]; then
        sudo cp "$WEBPORTAL_DIR/nginx.conf" /etc/nginx/sites-available/webportal
        sudo ln -sf /etc/nginx/sites-available/webportal /etc/nginx/sites-enabled/
        
        # Test nginx configuration
        if sudo nginx -t; then
            print_success "Nginx configuration installed"
        else
            print_error "Nginx configuration test failed!"
            return 1
        fi
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start WebPortal service
    sudo systemctl start webportal
    
    # Restart nginx if it's running
    if systemctl is-active --quiet nginx; then
        sudo systemctl reload nginx
        print_success "Nginx reloaded"
    fi
    
    # Check service status
    if systemctl is-active --quiet webportal; then
        print_success "WebPortal service started successfully"
    else
        print_error "WebPortal service failed to start!"
        print_status "Check logs: journalctl -u webportal -f"
        exit 1
    fi
}

# Function to run post-deployment tests
run_tests() {
    print_status "Running post-deployment tests..."
    
    # Wait for service to start
    sleep 3
    
    # Test if application is responding
    if curl -s http://localhost:5000/ > /dev/null; then
        print_success "Application is responding on port 5000"
    else
        print_warning "Application not responding on port 5000 (check if using different port)"
    fi
    
    # Test environment again
    source "$VENV_DIR/bin/activate"
    if python3 "$WEBPORTAL_DIR/validate_environment.py" > /dev/null 2>&1; then
        print_success "Environment validation passed"
    else
        print_warning "Environment validation has warnings (check manually)"
    fi
}

# Function to display deployment summary
show_summary() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    WEBPORTAL DEPLOYMENT SUMMARY${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "🏠 Installation Directory: $WEBPORTAL_DIR"
    echo "🐍 Python Virtual Environment: $VENV_DIR"
    echo "📋 Log File: $LOG_FILE"
    echo "💾 Backup Directory: $BACKUP_DIR"
    echo ""
    echo "🔧 Service Commands:"
    echo "  Start:   sudo systemctl start webportal"
    echo "  Stop:    sudo systemctl stop webportal"
    echo "  Restart: sudo systemctl restart webportal"
    echo "  Status:  sudo systemctl status webportal"
    echo "  Logs:    journalctl -u webportal -f"
    echo ""
    echo "📊 Monitoring:"
    echo "  Application: http://localhost:5000"
    echo "  Test page:   http://localhost:5000/test-notifications"
    echo "  Logs:        tail -f $LOG_FILE"
    echo ""
    echo "🔍 Validation:"
    echo "  Environment: python3 $WEBPORTAL_DIR/validate_environment.py"
    echo "  Database:    python3 $WEBPORTAL_DIR/backend/database_manager.py"
    echo ""
    print_success "Deployment completed successfully!"
}

# Main deployment function
main() {
    echo -e "${BLUE}🚀 WebPortal Production Deployment${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo ""
    
    # Pre-deployment checks
    check_root
    create_directories
    check_env_file
    
    # Setup components
    backup_existing
    setup_venv
    validate_environment
    setup_database
    set_permissions
    
    # Configure services
    setup_systemd_service
    setup_nginx
    
    # Start and test
    start_services
    run_tests
    
    # Show summary
    show_summary
}

# Handle command line arguments
case "${1:-}" in
    "validate")
        print_status "Running validation only..."
        check_env_file
        source "$VENV_DIR/bin/activate"
        python3 "$WEBPORTAL_DIR/validate_environment.py"
        ;;
    "database")
        print_status "Setting up database only..."
        check_env_file
        setup_venv
        setup_database
        ;;
    "restart")
        print_status "Restarting WebPortal service..."
        sudo systemctl restart webportal
        sudo systemctl reload nginx
        print_success "Services restarted"
        ;;
    "status")
        print_status "Checking service status..."
        systemctl status webportal
        ;;
    "logs")
        print_status "Showing logs..."
        journalctl -u webportal -f
        ;;
    "help"|"-h"|"--help")
        echo "WebPortal Deployment Script"
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (no args)  - Full deployment"
        echo "  validate   - Validate environment only"
        echo "  database   - Setup database only"
        echo "  restart    - Restart services"
        echo "  status     - Show service status"
        echo "  logs       - Show service logs"
        echo "  help       - Show this help"
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for available commands"
        exit 1
        ;;
esac