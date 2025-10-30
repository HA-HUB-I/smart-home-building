"""
Main routes for WebPortal
Home page, dashboard, general views
"""

from flask import render_template, jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.building import Building, Unit
from . import bp

@bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    stats = {
        'total_buildings': Building.query.count(),
        'total_units': Unit.query.count(),
        'total_users': User.query.count()
    }
    
    return render_template('main/index.html', stats=stats)

@bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '20251016120000'
    })

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with personalized information"""
    # Get user's memberships and buildings
    memberships = current_user.memberships.filter_by(is_active=True).all()
    
    context = {
        'user': current_user,
        'memberships': memberships,
        'has_buildings': len(memberships) > 0
    }
    
    return render_template('main/dashboard.html', **context)