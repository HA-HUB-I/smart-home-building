#!/bin/bash

# WebPortal Secure Deployment Script
# Generates secure production configuration without hardcoded sensitive data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 WebPortal Secure Deployment${NC}"
echo "======================================"

# Check if .env file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}❌ Error: .env file not found at $ENV_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}📁 Loading environment variables...${NC}"

# Load environment variables
set -a
source "$ENV_FILE"
set +a

echo -e "${YELLOW}🔍 Running smart security audit...${NC}"

# Run smart security audit
python3 "$SCRIPT_DIR/smart_security_audit.py"
AUDIT_RESULT=$?

if [[ $AUDIT_RESULT -ne 0 ]]; then
    echo -e "${RED}❌ Security audit failed! Please fix security issues before deployment.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Security audit passed!${NC}"

# Generate secure nginx configuration
echo -e "${YELLOW}🔧 Generating secure nginx configuration...${NC}"

cat > "$SCRIPT_DIR/nginx.conf.secure" << EOF
# WebPortal Secure Nginx Configuration
# Generated automatically with environment variables
# Date: $(date)

server {
    listen 80;
    server_name ${DOMAIN_NAME};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN_NAME};

    # SSL Configuration
    ssl_certificate ${SSL_CERT_PATH};
    ssl_certificate_key ${SSL_KEY_PATH};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/webportal.access.log;
    error_log /var/log/nginx/webportal.error.log;

    # Main Flask application
    location / {
        proxy_pass http://127.0.0.1:${FLASK_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Home Assistant Camera Proxy
    location /api/camera_proxy/ {
        proxy_pass http://${HA_HOST}:${HA_PORT}/api/camera_proxy/;
        proxy_set_header Host \$host;
        proxy_set_header Authorization "Bearer ${HA_API_TOKEN}";
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_buffering off;
    }

    # Static files (served directly by Nginx)
    location /static/ {
        alias ${APP_PATH}/backend/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Service Worker
    location /sw.js {
        proxy_pass http://127.0.0.1:${FLASK_PORT};
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # WebSocket proxy for Home Assistant  
    location /api/websocket {
        proxy_pass http://${HA_HOST}:${HA_PORT}/api/websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # Camera Stream Proxy
    location /api/camera_proxy_stream/ {
        proxy_pass http://${HA_HOST}:${HA_PORT}/api/camera_proxy_stream/;
        proxy_set_header Host \$host;
        proxy_set_header Authorization "Bearer ${HA_API_TOKEN}";
        proxy_set_header Connection "Upgrade";
        proxy_buffering off;
        proxy_set_header Connection "keep-alive";
        proxy_http_version 1.1;
    }

    # Favicon and manifest
    location = /favicon.ico {
        alias ${APP_PATH}/backend/favicon.ico;
        expires 1y;
    }

    location = /manifest.json {
        alias ${APP_PATH}/backend/static/manifest.json;
        add_header Content-Type application/json;
    }
}
EOF

echo -e "${GREEN}✅ Secure nginx configuration generated!${NC}"

echo -e "${YELLOW}🐍 Checking Python environment...${NC}"

# Check if virtual environment exists
if [[ -d "$SCRIPT_DIR/venv" ]]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"
    PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
else
    echo -e "${YELLOW}⚠️  No virtual environment found, using system python${NC}"
    PYTHON_CMD="python3"
fi

# Check required packages
echo -e "${YELLOW}📦 Checking Python dependencies...${NC}"
$PYTHON_CMD -c "
import sys
required_packages = {
    'flask': 'flask',
    'psycopg2': 'psycopg2',
    'python-dotenv': 'dotenv',
    'requests': 'requests'
}
missing = []
for pkg_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f'✓ {pkg_name}')
    except ImportError:
        missing.append(pkg_name)
        print(f'✗ {pkg_name} - MISSING')
        
if missing:
    print(f'\\n❌ Missing packages: {missing}')
    print('Install with: pip install ' + ' '.join(missing))
    sys.exit(1)
else:
    print('\\n✅ All required packages installed')
"

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Python dependencies check failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Testing application configuration...${NC}"

# Test configuration loading
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/backend')
try:
    from config import Config
    config = Config()
    config.validate_config()
    print('✅ Configuration validation passed')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Application configuration test failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🗄️  Testing database connection...${NC}"

# Test database connection
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
try:
    from backend.database_manager import DatabaseManager
    db = DatabaseManager()
    success = db.test_postgresql_connection()
    if success:
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Database error: {e}')
    sys.exit(1)
"

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Database connection test failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 DEPLOYMENT READY!${NC}"
echo "========================================"
echo -e "${BLUE}📋 Next steps:${NC}"
echo ""
echo "1. Review the secure nginx configuration:"
echo "   sudo nano $SCRIPT_DIR/nginx.conf.secure"
echo ""
echo "2. Copy to nginx sites-available:"
echo "   sudo cp $SCRIPT_DIR/nginx.conf.secure /etc/nginx/sites-available/webportal"
echo ""
echo "3. Enable the site:"
echo "   sudo ln -sf /etc/nginx/sites-available/webportal /etc/nginx/sites-enabled/"
echo ""
echo "4. Test nginx configuration:"
echo "   sudo nginx -t"
echo ""
echo "5. Start/reload nginx:"
echo "   sudo systemctl reload nginx"
echo ""
echo "6. Start the application (if not already running):"
echo "   cd $SCRIPT_DIR"
if [[ -d "$SCRIPT_DIR/venv" ]]; then
    echo "   source venv/bin/activate"
fi
echo "   python backend/app.py"
echo ""
echo -e "${GREEN}🔐 Security verified ✅${NC}"
echo -e "${GREEN}🗄️  Database ready ✅${NC}"
echo -e "${GREEN}🔧 Configuration valid ✅${NC}"
echo -e "${GREEN}🚀 Ready for production deployment!${NC}"