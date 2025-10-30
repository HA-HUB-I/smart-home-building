"""
Extensions & Integrations Blueprint
API management, webhooks, integrations, and custom fields
"""

from flask import Blueprint

bp = Blueprint('extensions', __name__, template_folder='templates')

from app.extensions import routes