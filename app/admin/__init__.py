"""
Admin Blueprint for WebPortal
Flask-Admin integration for administrative interface
"""

from flask import Blueprint
from .views import register_admin_views

bp = Blueprint('admin', __name__, url_prefix='/admin')

def init_admin(admin, db):
    """Initialize Flask-Admin with all model views"""
    register_admin_views(admin, db)
    return admin