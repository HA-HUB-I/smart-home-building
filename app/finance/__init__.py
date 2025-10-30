"""
Finance Blueprint - Financial management
Handles expenses, invoices, payments, and categories
"""

from flask import Blueprint

bp = Blueprint('finance', __name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes