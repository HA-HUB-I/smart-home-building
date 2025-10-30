#!/usr/bin/env python3
"""
Enhanced debug runner for WebPortal
"""
import os
import sys
from app import create_app

# Force reload of templates and static files
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['TEMPLATES_AUTO_RELOAD'] = '1'

app = create_app('development')

# Enhanced debug configuration
app.config.update(
    DEBUG=True,
    TEMPLATES_AUTO_RELOAD=True,
    SEND_FILE_MAX_AGE_DEFAULT=0,  # Disable static file caching
    EXPLAIN_TEMPLATE_LOADING=False  # Hide template loading info
)

if __name__ == '__main__':
    print("🚀 Starting WebPortal in Enhanced Debug Mode")
    print("📁 Templates will auto-reload on changes")
    print("🔄 Static files caching disabled")
    print("-" * 50)
    
    port = 5001
    for arg in sys.argv:
        if arg.startswith('--port='):
            port = int(arg.split('=')[1])
    
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=port,
        use_reloader=True,
        use_debugger=True,
        threaded=True
    )