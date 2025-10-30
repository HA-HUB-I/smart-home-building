"""
WebPortal Flask Application Factory
Production-ready modular architecture with PostgreSQL and Flask-Admin
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_login import LoginManager
from flask_session import Session
from werkzeug.security import generate_password_hash
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
sess = Session()

def create_app(config_name='production'):
    """Create and configure Flask application with modular architecture"""
    
    app = Flask(__name__)
    
    # Load configuration
    from config import Config
    app.config.from_object(Config)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Flask-Admin
    from flask_admin import Admin
    admin = Admin(app, name='WebPortal Admin', template_mode='bootstrap4')
    
    login_manager.init_app(app)
    sess.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Моля, влезте в системата за достъп до тази страница.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.buildings import bp as buildings_bp
    app.register_blueprint(buildings_bp, url_prefix='/buildings')
    
    from app.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
    
    from app.finance import bp as finance_bp
    app.register_blueprint(finance_bp, url_prefix='/finance')
    
    from app.communications import bp as communications_bp
    app.register_blueprint(communications_bp, url_prefix='/communications')
    
    from app.extensions import bp as extensions_bp
    app.register_blueprint(extensions_bp, url_prefix='/extensions')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Register admin views
    from app.admin.views import register_admin_views
    register_admin_views(admin, db)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Configure logging for production
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/webportal.log', 
                                         maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('WebPortal application startup')
    
    return app

# Import models to ensure they are registered with SQLAlchemy
from app.models import user, building, finance, system