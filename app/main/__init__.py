"""
Main Blueprint - Home page and general views
"""

from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes