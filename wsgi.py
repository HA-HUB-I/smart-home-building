#!/usr/bin/env python3
"""
WSGI Entry Point for WebPortal
Production WSGI configuration for Gunicorn
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Import the Flask application
from app import app

# Make it available as application for WSGI servers
application = app

if __name__ == "__main__":
    # For development/testing
    app.run(host='0.0.0.0', port=5000, debug=False)