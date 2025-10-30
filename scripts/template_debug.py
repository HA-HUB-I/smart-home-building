#!/usr/bin/env python3
"""
Template Debug Helper
Показва информация за зареждането на темплейти и debugging
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def enable_template_debugging():
    """Активира максимално ниво на template debugging"""
    
    # Environment променливи
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    os.environ['TEMPLATES_AUTO_RELOAD'] = '1'
    
    app = create_app('development')
    
    # Максимално debugging на темплейти
    app.config.update(
        DEBUG=True,
        TEMPLATES_AUTO_RELOAD=True,
        SEND_FILE_MAX_AGE_DEFAULT=0,
        EXPLAIN_TEMPLATE_LOADING=True,  # Показва template loading
    )
    
    # Jinja2 debugging
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}  # Изчистване на cache
    
    print("🔍 Template Debugging Information")
    print("=" * 40)
    print(f"Templates folder: {app.template_folder}")
    print(f"Templates auto-reload: {app.config['TEMPLATES_AUTO_RELOAD']}")
    print(f"Jinja2 auto-reload: {app.jinja_env.auto_reload}")
    print(f"Debug mode: {app.debug}")
    print(f"Template loading explanation: {app.config.get('EXPLAIN_TEMPLATE_LOADING')}")
    print("")
    print("🚀 Starting server with maximum template debugging...")
    print("📝 Template loading information will be shown in console")
    print("-" * 50)
    
    return app

if __name__ == '__main__':
    app = enable_template_debugging()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=True)