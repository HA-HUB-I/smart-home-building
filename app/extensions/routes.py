"""
Extensions Module Routes
Handles API management, webhooks, integrations, and custom extensions
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import bp
from app.models.user import User, LocalRoleEnum, Membership
from app.models.building import Building, Unit
from app.models import db
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def index():
    """Extensions dashboard - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    # Admin sees all buildings for management
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/dashboard.html', buildings=buildings, users=users)

@bp.route('/api-keys')
@login_required  
def api_keys():
    """API Keys management page - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/api_keys.html', buildings=buildings, users=users)

@bp.route('/webhooks')
@login_required
def webhooks():
    """Webhooks management page - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/webhooks.html', buildings=buildings, users=users)

@bp.route('/integrations')
@login_required
def integrations():
    """Integrations page - Home Assistant, IoT, etc. - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/integrations.html', buildings=buildings, users=users)

@bp.route('/payment-gateways')
@login_required
def payment_gateways():
    """Payment gateways configuration - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/payment_gateways.html', buildings=buildings, users=users)

@bp.route('/custom-fields')
@login_required
def custom_fields():
    """Custom fields management - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/custom_fields.html', buildings=buildings, users=users)

@bp.route('/plugins')
@login_required
def plugins():
    """Plugins and modules management - Admin only"""
    if not current_user.is_superuser:
        flash('Access denied. Extensions are available only for administrators.', 'error')
        return redirect(url_for('main.index'))
    
    buildings = Building.query.all()
    users = User.query.all()
    
    return render_template('extensions/plugins.html', buildings=buildings, users=users)

# API Endpoints
@bp.route('/api/test-webhook', methods=['POST'])
@login_required
def test_webhook():
    """Test webhook endpoint"""
    try:
        data = request.get_json()
        webhook_url = data.get('url')
        test_data = data.get('test_data', {'test': True, 'timestamp': datetime.utcnow().isoformat()})
        
        if not webhook_url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        # Send test webhook
        response = requests.post(webhook_url, json=test_data, timeout=10)
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'response_text': response.text[:200]  # Limit response text
        })
        
    except requests.RequestException as e:
        logger.error(f"Webhook test failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Webhook test error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    """Generate new API key"""
    try:
        data = request.get_json()
        building_id = data.get('building_id')
        key_name = data.get('name', 'API Key')
        permissions = data.get('permissions', [])
        
        # Verify user has access to building
        if not current_user.is_superuser:
            membership = Membership.query.filter_by(
                user_id=current_user.id,
                building_id=building_id,
                role=LocalRoleEnum.MANAGER
            ).first()
            
            if not membership:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Generate API key (simplified - in production use proper crypto)
        import secrets
        api_key = f"wpa_{secrets.token_urlsafe(32)}"
        
        # Store API key info (placeholder - implement APIKey model)
        api_key_data = {
            'key': api_key,
            'name': key_name,
            'building_id': building_id,
            'permissions': permissions,
            'created_by': current_user.id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"API key generated for building {building_id} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'api_key': api_key,
            'message': 'API key generated successfully'
        })
        
    except Exception as e:
        logger.error(f"API key generation error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to generate API key'}), 500

@bp.route('/api/test-integration', methods=['POST'])
@login_required
def test_integration():
    """Test external integration"""
    try:
        data = request.get_json()
        integration_type = data.get('type')
        config = data.get('config', {})
        
        if integration_type == 'home_assistant':
            # Test Home Assistant connection
            ha_url = config.get('url')
            ha_token = config.get('token')
            
            if not ha_url or not ha_token:
                return jsonify({'success': False, 'error': 'URL and token are required'}), 400
            
            headers = {'Authorization': f'Bearer {ha_token}'}
            response = requests.get(f"{ha_url}/api/", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return jsonify({'success': True, 'message': 'Home Assistant connection successful'})
            else:
                return jsonify({'success': False, 'error': f'Connection failed: {response.status_code}'}), 400
                
        elif integration_type == 'mqtt':
            # Test MQTT connection (placeholder)
            return jsonify({'success': True, 'message': 'MQTT test not implemented yet'})
            
        else:
            return jsonify({'success': False, 'error': 'Unknown integration type'}), 400
            
    except requests.RequestException as e:
        logger.error(f"Integration test failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Integration test error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/save-custom-field', methods=['POST'])
@login_required
def save_custom_field():
    """Save custom field configuration"""
    try:
        data = request.get_json()
        building_id = data.get('building_id')
        field_config = data.get('field_config')
        
        # Verify user has access to building
        if not current_user.is_superuser:
            membership = Membership.query.filter_by(
                user_id=current_user.id,
                building_id=building_id,
                role=LocalRoleEnum.MANAGER
            ).first()
            
            if not membership:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get building and update custom fields
        building = Building.query.get_or_404(building_id)
        
        if not building.settings:
            building.settings = {}
        
        if 'custom_fields' not in building.settings:
            building.settings['custom_fields'] = []
        
        # Add or update custom field
        field_name = field_config.get('name')
        existing_field = None
        
        for i, field in enumerate(building.settings['custom_fields']):
            if field.get('name') == field_name:
                existing_field = i
                break
        
        if existing_field is not None:
            building.settings['custom_fields'][existing_field] = field_config
        else:
            building.settings['custom_fields'].append(field_config)
        
        # Mark as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(building, 'settings')
        
        db.session.commit()
        
        logger.info(f"Custom field saved for building {building_id}: {field_name}")
        
        return jsonify({
            'success': True,
            'message': 'Custom field saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Custom field save error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to save custom field'}), 500