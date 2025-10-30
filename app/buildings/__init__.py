"""
Buildings Blueprint - Building and unit management
"""

from flask import Blueprint

bp = Blueprint('buildings', __name__)

from app.buildings import routes