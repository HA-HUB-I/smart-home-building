"""
Communications & Notifications Blueprint
Handles announcements, messages, notifications, and user communications
"""

from flask import Blueprint

bp = Blueprint('communications', __name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes