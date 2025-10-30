"""
Communications routes for managing announcements, messages, and notifications
"""

from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, date, timedelta

from . import bp
from app.models.system import Announcement
from app.models.building import Building, Unit
from app.models.user import User, Membership, LocalRoleEnum
from app import db


@bp.route('/')
@login_required
def index():
    """Communications dashboard with announcements and messages"""
    # Get accessible buildings for current user
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        # Get buildings where user has membership
        buildings_query = db.session.query(Building).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id
        ).distinct()
        buildings = buildings_query.all()
    
    # Get announcements visible to current user
    user_announcements = []
    for building in buildings:
        announcements = Announcement.query.filter_by(
            building_id=building.id,
            is_published=True
        ).order_by(desc(Announcement.created_at)).limit(10).all()
        
        # Filter by visibility rules
        visible_announcements = [
            ann for ann in announcements 
            if ann.is_visible_to_user(current_user)
        ]
        user_announcements.extend(visible_announcements)
    
    # Sort by urgency and creation date
    user_announcements.sort(key=lambda x: (x.is_urgent, x.created_at), reverse=True)
    
    # Get recent announcements count per building
    building_stats = []
    for building in buildings:
        recent_count = Announcement.query.filter(
            and_(
                Announcement.building_id == building.id,
                Announcement.created_at >= datetime.now() - timedelta(days=30),
                Announcement.is_published == True
            )
        ).count()
        
        unread_count = len([
            ann for ann in Announcement.query.filter_by(
                building_id=building.id, 
                is_published=True
            ).all()
            if ann.is_visible_to_user(current_user) and ann.is_current
        ])
        
        building_stats.append({
            'building': building,
            'recent_count': recent_count,
            'unread_count': unread_count
        })
    
    return render_template('communications/index.html',
                         announcements=user_announcements[:20],
                         building_stats=building_stats)


@bp.route('/announcements')
@login_required
def announcements():
    """List all announcements with filters"""
    # Get filters
    building_id = request.args.get('building_id', type=int)
    urgent_only = request.args.get('urgent', type=bool)
    author_id = request.args.get('author_id', type=int)
    
    # Base query
    query = Announcement.query.options(
        joinedload(Announcement.building),
        joinedload(Announcement.author)
    )
    
    # Apply building filter
    if building_id:
        query = query.filter_by(building_id=building_id)
    
    # Apply urgent filter
    if urgent_only:
        query = query.filter_by(is_urgent=True)
    
    # Apply author filter
    if author_id:
        query = query.filter_by(author_id=author_id)
    
    # Apply user access restrictions
    if not current_user.is_superuser:
        # Get accessible building IDs
        accessible_buildings = db.session.query(Building.id).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id
        ).distinct().subquery()
        query = query.filter(Announcement.building_id.in_(accessible_buildings))
    
    announcements = query.filter_by(is_published=True)\
        .order_by(desc(Announcement.is_urgent), desc(Announcement.created_at)).all()
    
    # Filter by visibility rules for current user
    visible_announcements = [
        ann for ann in announcements 
        if ann.is_visible_to_user(current_user)
    ]
    
    # Get buildings for filter dropdown
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id
        ).distinct().all()
    
    return render_template('communications/announcements.html',
                         announcements=visible_announcements,
                         buildings=buildings,
                         today=date.today(),
                         filters={
                             'building_id': building_id,
                             'urgent_only': urgent_only,
                             'author_id': author_id
                         })


@bp.route('/announcements/<int:announcement_id>')
@login_required
def view_announcement(announcement_id):
    """View announcement details"""
    announcement = Announcement.query.options(
        joinedload(Announcement.building),
        joinedload(Announcement.author)
    ).get_or_404(announcement_id)
    
    # Check if user can view this announcement
    if not announcement.is_visible_to_user(current_user):
        abort(403)
    
    # Increment view count
    announcement.increment_views()
    
    return render_template('communications/view.html',
                         announcement=announcement)


@bp.route('/announcements/new')
@login_required
def new_announcement():
    """Create new announcement"""
    # Get buildings where user can create announcements
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        # Only managers and owners can create announcements
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    if not buildings:
        flash('You do not have permission to create announcements.', 'error')
        return redirect(url_for('communications.announcements'))
    
    return render_template('communications/form.html',
                         available_buildings=buildings,
                         announcement=None,
                         today=date.today())


@bp.route('/announcements/<int:announcement_id>/edit')
@login_required
def edit_announcement(announcement_id):
    """Edit existing announcement"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check edit permissions
    if not (current_user.is_superuser or 
            announcement.author_id == current_user.id or
            current_user.has_role('manager', announcement.building)):
        abort(403)
    
    # Get buildings for dropdown (in case user wants to change building)
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    return render_template('communications/form.html',
                         available_buildings=buildings,
                         announcement=announcement,
                         today=date.today())


@bp.route('/announcements/create', methods=['POST'])
@login_required
def create_announcement():
    """Handle announcement creation"""
    building_id = request.form.get('building_id', type=int)
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    is_urgent = request.form.get('is_urgent', type=bool)
    visible_from = request.form.get('visible_from')
    visible_until = request.form.get('visible_until')
    
    # Audience targeting
    target_entrances = request.form.getlist('target_entrances')
    target_floors = request.form.getlist('target_floors', type=int)
    target_roles = request.form.getlist('target_roles')
    target_units = request.form.getlist('target_units', type=int)
    
    # Validation
    if not all([building_id, title, body]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('communications.new_announcement'))
    
    # Check permissions
    building = Building.query.get_or_404(building_id)
    if not (current_user.is_superuser or 
            current_user.has_role('manager', building)):
        abort(403)
    
    # Create announcement
    try:
        # Parse dates
        visible_from_date = None
        if visible_from:
            visible_from_date = datetime.strptime(visible_from, '%Y-%m-%d').date()
        
        visible_until_date = None
        if visible_until:
            visible_until_date = datetime.strptime(visible_until, '%Y-%m-%d').date()
        
        # Create audience targeting
        audience = {
            'entrances': target_entrances,
            'floors': target_floors,
            'roles': target_roles,
            'units': target_units
        }
        
        announcement = Announcement(
            building_id=building_id,
            author_id=current_user.id,
            title=title,
            body=body,
            is_urgent=is_urgent or False,
            visible_from=visible_from_date or date.today(),
            visible_until=visible_until_date,
            audience=audience
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash(f'Announcement "{title}" created successfully!', 'success')
        return redirect(url_for('communications.view_announcement', 
                              announcement_id=announcement.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating announcement: {str(e)}', 'error')
        return redirect(url_for('communications.new_announcement'))


@bp.route('/announcements/<int:announcement_id>/update', methods=['POST'])
@login_required
def update_announcement(announcement_id):
    """Handle announcement updates"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check edit permissions
    if not (current_user.is_superuser or 
            announcement.author_id == current_user.id or
            current_user.has_role('manager', announcement.building)):
        abort(403)
    
    # Update fields
    announcement.title = request.form.get('title', '').strip()
    announcement.body = request.form.get('body', '').strip()
    announcement.is_urgent = request.form.get('is_urgent', type=bool) or False
    
    # Update dates
    visible_from = request.form.get('visible_from')
    if visible_from:
        announcement.visible_from = datetime.strptime(visible_from, '%Y-%m-%d').date()
    
    visible_until = request.form.get('visible_until')
    if visible_until:
        announcement.visible_until = datetime.strptime(visible_until, '%Y-%m-%d').date()
    else:
        announcement.visible_until = None
    
    # Update audience
    announcement.audience = {
        'entrances': request.form.getlist('target_entrances'),
        'floors': request.form.getlist('target_floors', type=int),
        'roles': request.form.getlist('target_roles'),
        'units': request.form.getlist('target_units', type=int)
    }
    
    try:
        db.session.commit()
        flash('Announcement updated successfully!', 'success')
        return redirect(url_for('communications.view_announcement', 
                              announcement_id=announcement.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating announcement: {str(e)}', 'error')
        return redirect(url_for('communications.edit_announcement', 
                              announcement_id=announcement_id))


@bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    """Delete announcement"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check delete permissions
    if not (current_user.is_superuser or 
            announcement.author_id == current_user.id or
            current_user.has_role('manager', announcement.building)):
        abort(403)
    
    try:
        building_name = announcement.building.name
        announcement_title = announcement.title
        
        db.session.delete(announcement)
        db.session.commit()
        
        flash(f'Announcement "{announcement_title}" deleted successfully.', 'success')
        return redirect(url_for('communications.announcements'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting announcement: {str(e)}', 'error')
        return redirect(url_for('communications.view_announcement', 
                              announcement_id=announcement_id))


@bp.route('/notifications')
@login_required
def notifications():
    """User notifications center"""
    # Get user's notification preferences
    user_settings = current_user.settings or {}
    notification_settings = user_settings.get('notifications', {})
    
    # Get recent announcements as notifications
    user_buildings = db.session.query(Building).join(Unit).join(Membership).filter(
        Membership.user_id == current_user.id
    ).distinct().all()
    
    recent_announcements = []
    for building in user_buildings:
        announcements = Announcement.query.filter(
            and_(
                Announcement.building_id == building.id,
                Announcement.is_published == True,
                Announcement.created_at >= datetime.now() - timedelta(days=7)
            )
        ).order_by(desc(Announcement.created_at)).all()
        
        # Filter by visibility
        visible = [ann for ann in announcements if ann.is_visible_to_user(current_user)]
        recent_announcements.extend(visible)
    
    # Sort by urgency and date
    recent_announcements.sort(key=lambda x: (x.is_urgent, x.created_at), reverse=True)
    
    # Calculate stats
    stats = {
        'unread_count': len([n for n in recent_announcements if hasattr(n, 'is_urgent') and n.is_urgent]),
        'urgent_count': len([n for n in recent_announcements if hasattr(n, 'is_urgent') and n.is_urgent]),
        'total_count': len(recent_announcements),
        'today_count': len([n for n in recent_announcements if n.created_at.date() == datetime.utcnow().date()])
    }
    
    return render_template('communications/notifications.html',
                         notifications=recent_announcements,
                         notification_settings=notification_settings,
                         stats=stats)


@bp.route('/settings')
@login_required
def notification_settings():
    """Manage notification preferences"""
    user_settings = current_user.settings or {}
    notification_settings = user_settings.get('notifications', {
        'announcements': {'email': True, 'push': True, 'sms': False, 'app': True},
        'urgent': {'email': True, 'push': True, 'sms': True, 'app': True},
        'payments': {'email': True, 'push': True, 'sms': False, 'app': True},
        'building': {'email': True, 'push': True, 'sms': False, 'app': True},
        'meetings': {'email': True, 'push': True, 'sms': False, 'app': True},
    })
    
    general_settings = user_settings.get('general', {
        'timezone': 'Europe/Sofia',
        'language': 'bg',
        'quiet_hours': {'enabled': True, 'start_time': '22:00', 'end_time': '08:00'}
    })
    
    settings = {
        'notifications': notification_settings,
        'general': general_settings,
        'quiet_hours': general_settings.get('quiet_hours', {'enabled': True, 'start_time': '22:00', 'end_time': '08:00'})
    }
    
    return render_template('communications/settings.html',
                         settings=settings)


# API endpoints for AJAX calls
@bp.route('/api/buildings/<int:building_id>/units')
@login_required
def api_building_units(building_id):
    """Get units for targeting announcements"""
    # Check access to building
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            abort(403)
    
    units = Unit.query.filter_by(building_id=building_id).all()
    return jsonify([{
        'id': unit.id,
        'full_number': unit.full_number,
        'entrance': unit.entrance,
        'floor': unit.floor
    } for unit in units])


@bp.route('/api/announcements/<int:announcement_id>/mark-read', methods=['POST'])
@login_required
def api_mark_announcement_read(announcement_id):
    """Mark announcement as read by user"""
    # This would typically update a user_announcement_reads table
    # For now, we'll just return success
    return jsonify({'success': True})


@bp.route('/api/notifications/count')
@login_required
def api_notification_count():
    """Get unread notification count for current user"""
    # Get user's buildings
    user_buildings = db.session.query(Building.id).join(Unit).join(Membership).filter(
        Membership.user_id == current_user.id
    ).distinct().subquery()
    
    # Count current announcements
    unread_count = 0
    announcements = Announcement.query.filter(
        and_(
            Announcement.building_id.in_(user_buildings),
            Announcement.is_published == True
        )
    ).all()
    
    for ann in announcements:
        if ann.is_visible_to_user(current_user) and ann.is_current:
            unread_count += 1
    
    return jsonify({'count': unread_count})


@bp.route('/api/buildings/<int:building_id>/entrances')
@login_required
def api_building_entrances(building_id):
    """Get entrances for a building"""
    # Check access to building
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            abort(403)
    
    # Get building and its entrances
    building = Building.query.get_or_404(building_id)
    entrances = db.session.query(Unit.entrance).filter(
        Unit.building_id == building_id
    ).distinct().all()
    
    entrance_list = [entrance[0] for entrance in entrances if entrance[0]]
    
    return jsonify({'entrances': entrance_list})