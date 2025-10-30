"""
Buildings routes for WebPortal
Building and unit management views
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.building import Building, Unit
from app.models.user import Membership
from app import db
from . import bp

@bp.route('/')
@login_required
def index():
    """Buildings listing page"""
    # Get buildings based on user role
    if current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']:
        # Admin can see all buildings
        buildings = Building.query.all()
    else:
        # Regular user sees only their buildings
        building_ids = db.session.query(Building.id).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.is_active == True
        ).distinct().all()
        building_ids = [bid[0] for bid in building_ids]
        buildings = Building.query.filter(Building.id.in_(building_ids)).all() if building_ids else []
    
    return render_template('buildings/index.html', buildings=buildings)

@bp.route('/building/<int:id>')
@login_required 
def view_building(id):
    """View specific building details"""
    building = Building.query.get_or_404(id)
    
    # Check if user has access to this building
    if not current_user.is_superuser and current_user.global_role.value not in ['superadmin', 'staff']:
        user_building_ids = db.session.query(Building.id).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.is_active == True
        ).distinct().all()
        user_building_ids = [bid[0] for bid in user_building_ids]
        
        if building.id not in user_building_ids:
            flash('Нямате достъп до тази сграда.', 'error')
            return redirect(url_for('buildings.index'))
    
    # Get units grouped by entrance and floor
    units = Unit.query.filter_by(building_id=id).order_by(
        Unit.entrance, Unit.floor, Unit.number
    ).all()
    
    # Group units by entrance
    units_by_entrance = {}
    for unit in units:
        entrance = unit.entrance or 'Без вход'
        if entrance not in units_by_entrance:
            units_by_entrance[entrance] = {}
        
        floor = unit.floor or 0
        if floor not in units_by_entrance[entrance]:
            units_by_entrance[entrance][floor] = []
        
        units_by_entrance[entrance][floor].append(unit)
    
    return render_template('buildings/detail.html', 
                         building=building, 
                         units_by_entrance=units_by_entrance)

@bp.route('/building/<int:building_id>/unit/<int:unit_id>')
@login_required
def view_unit(building_id, unit_id):
    """View specific unit details"""
    unit = Unit.query.filter_by(id=unit_id, building_id=building_id).first_or_404()
    
    # Check access
    if not current_user.is_superuser and current_user.global_role.value not in ['superadmin', 'staff']:
        membership = Membership.query.filter_by(
            user_id=current_user.id,
            unit_id=unit_id,
            is_active=True
        ).first()
        
        if not membership:
            flash('Нямате достъп до този обект.', 'error')
            return redirect(url_for('buildings.view_building', id=building_id))
    
    # Get all memberships for this unit
    memberships = Membership.query.filter_by(unit_id=unit_id).all()
    
    return render_template('buildings/unit_detail.html', 
                         unit=unit, 
                         memberships=memberships)

@bp.route('/api/buildings')
@login_required
def api_buildings():
    """API endpoint for buildings data"""
    buildings = []
    
    if current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']:
        # Admin can see all buildings
        query_buildings = Building.query.all()
    else:
        # Regular user sees only their buildings
        building_ids = db.session.query(Building.id).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.is_active == True
        ).distinct().all()
        building_ids = [bid[0] for bid in building_ids]
        query_buildings = Building.query.filter(Building.id.in_(building_ids)).all() if building_ids else []
    
    for building in query_buildings:
        buildings.append({
            'id': building.id,
            'name': building.name,
            'address': building.address,
            'entrances': building.entrances,
            'total_units': len(building.units),
            'is_active': building.is_active
        })
    
    return jsonify(buildings)

@bp.route('/search')
@login_required
def search():
    """Search buildings and units"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('buildings/search.html', results=None, query='')
    
    # Search in buildings and units
    buildings = Building.query.filter(Building.name.ilike(f'%{query}%')).all()
    units = Unit.query.join(Building).filter(
        db.or_(
            Unit.number.ilike(f'%{query}%'),
            Building.name.ilike(f'%{query}%')
        )
    ).all()
    
    # Filter results based on user access
    if not (current_user.is_superuser or current_user.global_role.value in ['superadmin', 'staff']):
        user_building_ids = db.session.query(Building.id).join(Unit).join(Membership).filter(
            Membership.user_id == current_user.id,
            Membership.is_active == True
        ).distinct().all()
        user_building_ids = [bid[0] for bid in user_building_ids]
        
        buildings = [b for b in buildings if b.id in user_building_ids]
        units = [u for u in units if u.building_id in user_building_ids]
    
    results = {
        'buildings': buildings,
        'units': units,
        'total': len(buildings) + len(units)
    }
    
    return render_template('buildings/search.html', results=results, query=query)