"""
Production Configuration for WebPortal
Enhanced with PostgreSQL, SQLAlchemy, and environment-based settings
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Base configuration with secure defaults"""
    
    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        # Handle Heroku postgres:// URLs
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or \
        f"postgresql://{os.environ.get('DB_USER', 'webportal')}:" \
        f"{os.environ.get('DB_PASSWORD', 'password')}@" \
        f"{os.environ.get('DB_HOST', 'localhost')}:" \
        f"{os.environ.get('DB_PORT', '5432')}/" \
        f"{os.environ.get('DB_NAME', 'webportal_db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'webportal:'
    
    # Security Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Home Assistant Integration
    HA_API_URL = os.environ.get('HA_API_URL', 'http://192.168.1.67:8123/api')
    HA_API_TOKEN = os.environ.get('HA_API_TOKEN')
    HA_BASE_URL = os.environ.get('HA_BASE_URL', 'http://192.168.1.67:8123')
    
    # Telegram Notifications
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    # Push Notifications
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_CLAIMS = {"sub": "mailto:admin@unlck.app"}
    
    # Application Version
    LAST_DEPLOYMENT_TIMESTAMP = os.environ.get('DEPLOYMENT_TIMESTAMP', '20251016120000')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Cache Settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Admin Settings
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@webportal.local')
    
    # Flask-Admin Settings
    FLASK_ADMIN_SWATCH = 'cerulean'
    
    # Extension System
    EXTENSIONS_FOLDER = os.path.join(basedir, 'app', 'extensions')
    ENABLE_EXTENSIONS = os.environ.get('ENABLE_EXTENSIONS', 'true').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Sensor and Camera Configuration (backwards compatibility)
SENSORS = [
    {
        "entity_id": "weather.openweathermap",
        "attributes": ["temperature", "humidity", "wind_speed", "weather"]
    },
    {
        "entity_id": "binary_sensor.entrance_door",
        "attributes": ["state"]
    },
    {
        "entity_id": "sensor.wifi_signal_strength",
        "attributes": ["state"]
    }
]

CAMERAS = [
    {
        "entity_id": "camera.esp32cam_my_cam",
        "name": "Входна врата",
        "source": "ha"
    },
    {
        "entity_id": "camera.hikvision_entrance",
        "name": "Главен вход", 
        "source": "ha"
    }
]