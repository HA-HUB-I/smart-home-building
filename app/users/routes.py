"""
Users routes for WebPortal
User management, memberships, permissions
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.user import User, Membership, GlobalRoleEnum, LocalRoleEnum
from app.models.building import Building, Unit
from app import db
from . import bp

@bp.route('/')
@login_required
def index():
    """Users listing page"""
    # Check if user has admin rights
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        flash('Нямате права за достъп до тази страница.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all users with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Search functionality
    search = request.args.get('search', '', type=str)
    filter_role = request.args.get('role', '', type=str)
    filter_active = request.args.get('active', '', type=str)
    
    # Build query
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.phone.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    
    if filter_role:
        query = query.filter(User.global_role == GlobalRoleEnum(filter_role))
    
    if filter_active == 'true':
        query = query.filter(User.is_active == True)
    elif filter_active == 'false':
        query = query.filter(User.is_active == False)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'superusers': User.query.filter_by(is_superuser=True).count(),
        'verified_users': User.query.filter_by(is_verified=True).count()
    }
    
    return render_template('users/index.html', 
                         users=users, 
                         stats=stats,
                         search=search,
                         filter_role=filter_role,
                         filter_active=filter_active)

@bp.route('/user/<int:id>')
@login_required
def view_user(id):
    """View specific user details"""
    user = User.query.get_or_404(id)
    
    # Check access rights
    if not (current_user.is_superuser or 
            current_user.global_role.value in ['superadmin', 'staff'] or
            current_user.id == id):
        flash('Нямате права за достъп до този профил.', 'error')
        return redirect(url_for('users.index'))
    
    # Get user's memberships
    memberships = Membership.query.filter_by(user_id=id).all()
    
    # Get user's buildings (for admins)
    buildings = []
    if current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']:
        building_ids = [m.unit.building_id for m in memberships]
        buildings = Building.query.filter(Building.id.in_(building_ids)).distinct().all() if building_ids else []
    
    return render_template('users/detail.html', 
                         user=user, 
                         memberships=memberships,
                         buildings=buildings)

@bp.route('/user/<int:id>/memberships')
@login_required
def user_memberships(id):
    """User memberships management"""
    user = User.query.get_or_404(id)
    
    # Check access rights
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        flash('Нямате права за управление на членства.', 'error')
        return redirect(url_for('users.view_user', id=id))
    
    memberships = Membership.query.filter_by(user_id=id).all()
    available_buildings = Building.query.filter_by(is_active=True).all()
    
    return render_template('users/memberships.html', 
                         user=user, 
                         memberships=memberships,
                         available_buildings=available_buildings,
                         roles=LocalRoleEnum)

@bp.route('/user/<int:user_id>/membership/add', methods=['POST'])
@login_required
def add_membership(user_id):
    """Add membership to user"""
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        flash('Нямате права за добавяне на членства.', 'error')
        return redirect(url_for('users.view_user', id=user_id))
    
    unit_id = request.form.get('unit_id')
    role = request.form.get('role')
    is_primary = bool(request.form.get('is_primary'))
    
    if not unit_id or not role:
        flash('Моля изберете обект и роля.', 'error')
        return redirect(url_for('users.user_memberships', id=user_id))
    
    # Check if membership already exists
    existing = Membership.query.filter_by(user_id=user_id, unit_id=unit_id).first()
    if existing:
        flash('Потребителят вече има членство в този обект.', 'error')
        return redirect(url_for('users.user_memberships', id=user_id))
    
    # Create new membership
    membership = Membership(
        user_id=user_id,
        unit_id=unit_id,
        role=LocalRoleEnum(role),
        is_primary=is_primary,
        is_active=True
    )
    
    try:
        db.session.add(membership)
        db.session.commit()
        flash('Членството е добавено успешно.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Грешка при добавяне на членството.', 'error')
    
    return redirect(url_for('users.user_memberships', id=user_id))

@bp.route('/membership/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_membership(id):
    """Toggle membership active status"""
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        return jsonify({'error': 'Unauthorized'}), 403
    
    membership = Membership.query.get_or_404(id)
    membership.is_active = not membership.is_active
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'is_active': membership.is_active,
            'message': f'Членството е {"активирано" if membership.is_active else "деактивирано"}.'
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

@bp.route('/api/users')
@login_required
def api_users():
    """API endpoint for users data"""
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = []
    for user in User.query.all():
        users.append({
            'id': user.id,
            'email': user.email,
            'phone': user.phone,
            'full_name': user.full_name,
            'global_role': user.global_role.value if user.global_role else 'resident',
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'is_verified': user.is_verified,
            'memberships_count': len(user.memberships.filter_by(is_active=True).all()),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat()
        })
    
    return jsonify(users)

@bp.route('/api/units/<int:building_id>')
@login_required
def api_building_units(building_id):
    """Get units for a specific building (for AJAX forms)"""
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        return jsonify({'error': 'Unauthorized'}), 403
    
    units = Unit.query.filter_by(building_id=building_id, is_active=True).all()
    units_data = []
    
    for unit in units:
        units_data.append({
            'id': unit.id,
            'full_number': unit.full_number,
            'entrance': unit.entrance,
            'floor': unit.floor,
            'number': unit.number,
            'has_active_membership': bool(any(m.is_active for m in unit.memberships))
        })
    
    return jsonify(units_data)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create new user"""
    # Check if user has admin rights
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        flash('Нямате права за достъп до тази страница.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            email = request.form.get('email')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name') 
            phone = request.form.get('phone')
            password = request.form.get('password', 'changeme123')
            global_role = request.form.get('global_role', 'resident')
            is_active = request.form.get('is_active') == 'on'
            
            # Validate required fields
            if not email:
                flash('Имейлът е задължителен.', 'error')
                return render_template('users/new.html')
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                flash('Потребител с този имейл вече съществува.', 'error')
                return render_template('users/new.html')
            
            # Create new user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_active=is_active,
                global_role=GlobalRoleEnum(global_role)
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Потребителят {email} беше създаден успешно.', 'success')
            return redirect(url_for('users.view_user', id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при създаване на потребител: {str(e)}', 'error')
            return render_template('users/new.html')
    
    return render_template('users/new.html')

@bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit user details"""
    user = User.query.get_or_404(id)
    
    # Check access rights - admin or own profile
    if not (current_user.is_superuser or 
            current_user.global_role.value in ['superadmin', 'staff'] or
            current_user.id == id):
        flash('Нямате права за редактиране на този потребител.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            email = request.form.get('email')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name') 
            phone = request.form.get('phone')
            is_active = request.form.get('is_active') == 'on'
            
            # Only admin can change global role
            if current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']:
                global_role = request.form.get('global_role', user.global_role.value)
                user.global_role = GlobalRoleEnum(global_role)
                user.is_active = is_active
            
            # Validate required fields
            if not email:
                flash('Имейлът е задължителен.', 'error')
                return render_template('users/edit.html', user=user)
            
            # Check if email is taken by another user
            existing_user = User.query.filter(User.email == email, User.id != id).first()
            if existing_user:
                flash('Потребител с този имейл вече съществува.', 'error')
                return render_template('users/edit.html', user=user)
            
            # Update user data
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.phone = phone
            
            # Handle password change
            new_password = request.form.get('new_password')
            if new_password and new_password.strip():
                user.set_password(new_password)
                flash('Паролата беше променена.', 'info')
            
            db.session.commit()
            
            flash(f'Потребителят {email} беше актуализиран успешно.', 'success')
            return redirect(url_for('users.view_user', id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при актуализиране на потребител: {str(e)}', 'error')
            return render_template('users/edit.html', user=user)
    
    return render_template('users/edit.html', user=user)

@bp.route('/me')
@login_required
def my_profile():
    """Current user's profile - shortcut"""
    return redirect(url_for('users.view_user', id=current_user.id))

@bp.route('/me/edit')
@login_required 
def edit_my_profile():
    """Current user's profile edit - shortcut"""
    return redirect(url_for('users.edit_user', id=current_user.id))

@bp.route('/search')
@login_required
def search():
    """User search page"""
    # Check if user has admin rights
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        flash('Нямате права за достъп до тази страница.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('users/search.html')