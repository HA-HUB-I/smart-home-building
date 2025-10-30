"""
API Blueprint - REST API endpoints
"""

from flask import Blueprint

bp = Blueprint('api', __name__)

@bp.route('/status')
def status():
    return {"status": "API under construction"}