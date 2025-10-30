"""
Finance routes for managing expenses, invoices, payments, and categories
"""

from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import desc, func, and_, extract
from datetime import datetime, date
import calendar

from . import bp
from app.models.finance import (
    ExpenseCategory, Expense, ExpenseAllocation, 
    Invoice, Payment, InvoiceStatusEnum, PaymentMethodEnum,
    AllocationMethodEnum
)
from app.models.building import Building, Unit
from app.models.user import User, Membership, LocalRoleEnum
from app import db


@bp.route('/')
@login_required
def index():
    """Finance dashboard with overview statistics"""
    # Get accessible buildings for current user
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        # Get buildings where user has financial role (manager, cashier, owner)
        buildings_query = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct()
        buildings = buildings_query.all()
    
    # Get current month/year for statistics
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Calculate statistics for each building
    building_stats = []
    for building in buildings:
        # Get monthly expenses for current month
        monthly_expenses = db.session.query(func.sum(Expense.amount_total)).filter(
            and_(
                Expense.building_id == building.id,
                extract('month', Expense.period) == current_month,
                extract('year', Expense.period) == current_year
            )
        ).scalar() or 0
        
        # Get unpaid invoices
        unpaid_amount = db.session.query(func.sum(Invoice.amount_due)).filter(
            and_(
                Invoice.unit.has(Unit.building_id == building.id),
                Invoice.status != InvoiceStatusEnum.PAID
            )
        ).scalar() or 0
        
        # Get paid amount this month
        paid_amount = db.session.query(func.sum(Payment.amount)).join(Invoice).join(Unit).filter(
            and_(
                Unit.building_id == building.id,
                extract('month', Payment.paid_at) == current_month,
                extract('year', Payment.paid_at) == current_year
            )
        ).scalar() or 0
        
        building_stats.append({
            'building': building,
            'monthly_expenses': float(monthly_expenses),
            'unpaid_amount': float(unpaid_amount),
            'paid_amount': float(paid_amount),
            'units_count': Unit.query.filter_by(building_id=building.id).count()
        })
    
    return render_template('finance/index.html',
                         building_stats=building_stats,
                         current_month_name=calendar.month_name[current_month],
                         current_year=current_year)


@bp.route('/building/<int:building_id>')
@login_required
def building_finance(building_id):
    """Finance overview for specific building"""
    building = Building.query.get_or_404(building_id)
    
    # Check access permissions
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            abort(403)
    
    # Get expense categories for this building
    categories = ExpenseCategory.query.filter_by(building_id=building_id).all()
    
    # Get recent expenses (last 6 months)
    recent_expenses = Expense.query.filter_by(building_id=building_id)\
        .order_by(desc(Expense.period))\
        .limit(20).all()
    
    # Get overdue invoices
    overdue_invoices = Invoice.query.join(Unit).filter(
        and_(
            Unit.building_id == building_id,
            Invoice.status == InvoiceStatusEnum.OVERDUE
        )
    ).all()
    
    # Get units with unpaid amounts
    units_with_debt = db.session.query(Unit, func.sum(Invoice.amount_due).label('total_debt'))\
        .join(Invoice)\
        .filter(
            and_(
                Unit.building_id == building_id,
                Invoice.status != InvoiceStatusEnum.PAID
            )
        )\
        .group_by(Unit.id)\
        .having(func.sum(Invoice.amount_due) > 0)\
        .all()
    
    return render_template('finance/building.html',
                         building=building,
                         categories=categories,
                         recent_expenses=recent_expenses,
                         overdue_invoices=overdue_invoices,
                         units_with_debt=units_with_debt)


@bp.route('/expenses')
@login_required
def expenses():
    """List all expenses with filters"""
    # Get building filter
    building_id = request.args.get('building_id', type=int)
    category_id = request.args.get('category_id', type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    
    # Base query
    query = Expense.query.options(
        joinedload(Expense.building),
        joinedload(Expense.category)
    )
    
    # Apply filters
    if building_id:
        query = query.filter_by(building_id=building_id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if year:
        query = query.filter(extract('year', Expense.period) == year)
    if month:
        query = query.filter(extract('month', Expense.period) == month)
    
    # Apply user access restrictions
    if not current_user.is_superuser:
        accessible_buildings = db.session.query(Building.id).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().subquery()
        query = query.filter(Expense.building_id.in_(accessible_buildings))
    
    expenses = query.order_by(desc(Expense.period)).all()
    
    # Get buildings for filter dropdown
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    # Get categories for filter
    categories = ExpenseCategory.query.all() if current_user.is_superuser else \
        ExpenseCategory.query.filter(
            ExpenseCategory.building_id.in_([b.id for b in buildings])
        ).all()
    
    return render_template('finance/expenses.html',
                         expenses=expenses,
                         buildings=buildings,
                         categories=categories,
                         filters={
                             'building_id': building_id,
                             'category_id': category_id,
                             'year': year,
                             'month': month
                         })


@bp.route('/expenses/new', methods=['GET', 'POST'])
@login_required
def new_expense():
    """Create new expense"""
    # Get accessible buildings
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
            )
        ).distinct().all()
    
    if not buildings:
        flash('You do not have permission to create expenses.', 'error')
        return redirect(url_for('finance.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            building_id = request.form.get('building_id', type=int)
            category_id = request.form.get('category_id', type=int)
            period_str = request.form.get('period')
            amount_total = request.form.get('amount_total', type=float)
            description = request.form.get('description', '').strip()
            
            # Validate required fields
            if not all([building_id, category_id, period_str, amount_total]):
                flash('Всички полета са задължителни.', 'error')
                return render_template('finance/expenses/new.html', buildings=buildings, expense=None)
            
            # Parse period (YYYY-MM format to first day of month)
            try:
                period_date = datetime.strptime(period_str + '-01', '%Y-%m-%d').date()
            except ValueError:
                flash('Невалиден формат на периода.', 'error')
                return render_template('finance/expenses/new.html', buildings=buildings, expense=None)
            
            # Check if user has access to this building
            if not current_user.is_superuser:
                has_access = db.session.query(Membership).join(Unit).filter(
                    and_(
                        Unit.building_id == building_id,
                        Membership.user_id == current_user.id,
                        Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                    )
                ).first()
                if not has_access:
                    flash('Няmate достъп до тази сграда.', 'error')
                    return render_template('finance/expenses/new.html', buildings=buildings, expense=None)
            
            # Get category and validate
            category = ExpenseCategory.query.filter_by(id=category_id, building_id=building_id).first()
            if not category:
                flash('Невалидна категория за избраната сграда.', 'error')
                return render_template('finance/expenses/new.html', buildings=buildings, expense=None)
            
            # Create expense
            expense = Expense(
                building_id=building_id,
                category_id=category_id,
                period=period_date,
                amount_total=amount_total,
                notes=description
            )
            
            db.session.add(expense)
            db.session.commit()
            
            flash('Разходът беше създаден успешно!', 'success')
            return redirect(url_for('finance.view_expense', expense_id=expense.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при създаване на разхода: {str(e)}', 'error')
            return render_template('finance/expenses/new.html', buildings=buildings, expense=None)
    
    return render_template('finance/expenses/new.html',
                         buildings=buildings,
                         expense=None)


@bp.route('/expenses/<int:expense_id>')
@login_required
def view_expense(expense_id):
    """View expense details with allocations"""
    expense = Expense.query.options(
        joinedload(Expense.building),
        joinedload(Expense.category),
        joinedload(Expense.allocations).joinedload(ExpenseAllocation.unit)
    ).get_or_404(expense_id)
    
    # Check access
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == expense.building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            abort(403)
    
    return render_template('finance/expense_detail.html', expense=expense)


@bp.route('/invoices')
@login_required
def invoices():
    """List invoices with filters"""
    # Filters
    building_id = request.args.get('building_id', type=int)
    unit_id = request.args.get('unit_id', type=int)
    status = request.args.get('status')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    
    # Base query
    query = Invoice.query.options(
        joinedload(Invoice.unit).joinedload(Unit.building)
    )
    
    # Apply filters
    if building_id:
        query = query.join(Unit).filter(Unit.building_id == building_id)
    if unit_id:
        query = query.filter_by(unit_id=unit_id)
    if status:
        query = query.filter_by(status=InvoiceStatusEnum(status))
    if year:
        query = query.filter(extract('year', Invoice.period) == year)
    if month:
        query = query.filter(extract('month', Invoice.period) == month)
    
    # Apply user access restrictions
    if not current_user.is_superuser:
        accessible_buildings = db.session.query(Building.id).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().subquery()
        query = query.join(Unit).filter(Unit.building_id.in_(accessible_buildings))
    
    invoices = query.order_by(desc(Invoice.period)).all()
    
    # Get data for filters
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    return render_template('finance/invoices.html',
                         invoices=invoices,
                         buildings=buildings,
                         invoice_statuses=InvoiceStatusEnum,
                         filters={
                             'building_id': building_id,
                             'unit_id': unit_id,
                             'status': status,
                             'year': year,
                             'month': month
                         })


@bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.options(
        joinedload(Invoice.unit).joinedload(Unit.building),
        joinedload(Invoice.payments)
    ).get_or_404(invoice_id)
    
    # Check access
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == invoice.unit.building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            abort(403)
    
    return render_template('finance/invoice_detail.html', invoice=invoice)


@bp.route('/payments')
@login_required
def payments():
    """List payments with filters"""
    # Filters
    building_id = request.args.get('building_id', type=int)
    method = request.args.get('method')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    
    # Base query
    query = Payment.query.options(
        joinedload(Payment.unit).joinedload(Unit.building),
        joinedload(Payment.invoice)
    )
    
    # Apply filters
    if building_id:
        query = query.join(Unit).filter(Unit.building_id == building_id)
    if method:
        query = query.filter_by(method=PaymentMethodEnum(method))
    if year:
        query = query.filter(extract('year', Payment.paid_at) == year)
    if month:
        query = query.filter(extract('month', Payment.paid_at) == month)
    
    # Apply user access restrictions
    if not current_user.is_superuser:
        accessible_buildings = db.session.query(Building.id).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().subquery()
        query = query.join(Unit).filter(Unit.building_id.in_(accessible_buildings))
    
    payments = query.order_by(desc(Payment.paid_at)).all()
    
    # Get data for filters
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    return render_template('finance/payments.html',
                         payments=payments,
                         buildings=buildings,
                         payment_methods=PaymentMethodEnum,
                         filters={
                             'building_id': building_id,
                             'method': method,
                             'year': year,
                             'month': month
                         })


@bp.route('/payments/new')
@login_required
def new_payment():
    """Record new payment"""
    # Get invoice_id if coming from invoice page
    invoice_id = request.args.get('invoice_id', type=int)
    invoice = None
    if invoice_id:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        # Check access
        if not current_user.is_superuser:
            has_access = db.session.query(Membership).join(Unit).filter(
                and_(
                    Unit.building_id == invoice.unit.building_id,
                    Membership.user_id == current_user.id,
                    Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                )
            ).first()
            if not has_access:
                abort(403)
    
    return render_template('finance/payment_form.html',
                         invoice=invoice,
                         payment_methods=PaymentMethodEnum)


@bp.route('/categories')
@login_required
def categories():
    """Manage expense categories"""
    # Get accessible buildings
    if current_user.is_superuser:
        buildings = Building.query.all()
        categories = ExpenseCategory.query.options(joinedload(ExpenseCategory.building)).all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
            )
        ).distinct().all()
        
        building_ids = [b.id for b in buildings]
        categories = ExpenseCategory.query.options(joinedload(ExpenseCategory.building))\
            .filter(ExpenseCategory.building_id.in_(building_ids)).all()
    
    return render_template('finance/categories.html',
                         categories=categories,
                         buildings=buildings,
                         allocation_methods=AllocationMethodEnum)


@bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    """Create new expense category"""
    # Get accessible buildings
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
            )
        ).distinct().all()
    
    if not buildings:
        flash('Няmate достъп до нито една сграда за създаване на категории.', 'error')
        return redirect(url_for('finance.categories'))
    
    if request.method == 'POST':
        try:
            # Get form data
            building_id = request.form.get('building_id', type=int)
            code = request.form.get('code', '').strip().lower()
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            allocation_method = request.form.get('allocation_method')
            is_active = bool(request.form.get('is_active'))
            
            # Validate required fields
            if not all([building_id, code, name, allocation_method]):
                flash('Всички задължителни полета трябва да бъдат попълнени.', 'error')
                return render_template('finance/categories/new.html', buildings=buildings)
            
            # Check building access
            if not current_user.is_superuser:
                has_access = db.session.query(Membership).join(Unit).filter(
                    and_(
                        Unit.building_id == building_id,
                        Membership.user_id == current_user.id,
                        Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                    )
                ).first()
                if not has_access:
                    flash('Няmate достъп до тази сграда.', 'error')
                    return render_template('finance/categories/new.html', buildings=buildings)
            
            # Validate code format
            import re
            if not re.match(r'^[a-z_]+$', code):
                flash('Кодът може да съдържа само малки латински букви и подчертавки.', 'error')
                return render_template('finance/categories/new.html', buildings=buildings)
            
            # Check if code is unique in building
            existing = ExpenseCategory.query.filter_by(
                building_id=building_id, 
                code=code
            ).first()
            if existing:
                flash('Категория с този код вече съществува в избраната сграда.', 'error')
                return render_template('finance/categories/new.html', buildings=buildings)
            
            # Validate allocation method
            try:
                allocation_method_enum = AllocationMethodEnum(allocation_method)
            except ValueError:
                flash('Невалиден метод на разпределение.', 'error')
                return render_template('finance/categories/new.html', buildings=buildings)
            
            # Build settings from advanced options
            settings = {
                'auto_generate': bool(request.form.get('auto_generate')),
                'notifications': bool(request.form.get('notifications'))
            }
            
            # Add optional settings
            default_amount = request.form.get('default_amount')
            if default_amount:
                settings['default_amount'] = float(default_amount)
            
            sort_order = request.form.get('sort_order')
            if sort_order:
                settings['order'] = int(sort_order)
            
            custom_settings = request.form.get('custom_settings')
            if custom_settings:
                import json
                try:
                    custom = json.loads(custom_settings)
                    settings.update(custom)
                except json.JSONDecodeError:
                    flash('Невалиден JSON в допълнителните настройки.', 'error')
                    return render_template('finance/categories/new.html', buildings=buildings)
            
            # Create category
            category = ExpenseCategory(
                building_id=building_id,
                code=code,
                name=name,
                description=description,
                allocation_method=allocation_method_enum,
                is_active=is_active,
                settings=settings
            )
            
            db.session.add(category)
            db.session.commit()
            
            flash('Категорията е създадена успешно!', 'success')
            return redirect(url_for('finance.categories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при създаване на категорията: {str(e)}', 'error')
            return render_template('finance/categories/new.html', buildings=buildings)
    
    return render_template('finance/categories/new.html', buildings=buildings)


@bp.route('/reports')
@login_required
def reports():
    """Financial reports and analytics"""
    # Get accessible buildings
    if current_user.is_superuser:
        buildings = Building.query.all()
    else:
        buildings = db.session.query(Building).join(Unit).join(Membership).filter(
            and_(
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).distinct().all()
    
    return render_template('finance/reports.html', buildings=buildings)


# API endpoints for AJAX calls and data handling will go here
@bp.route('/api/units/<int:building_id>')
@login_required
def api_units_by_building(building_id):
    """Get units for a building (for form dropdowns)"""
    units = Unit.query.filter_by(building_id=building_id).all()
    return jsonify([{
        'id': unit.id,
        'full_number': unit.full_number
    } for unit in units])


@bp.route('/api/categories/<int:building_id>')
@login_required  
def api_categories_by_building(building_id):
    """Get expense categories for a building"""
    categories = ExpenseCategory.query.filter_by(building_id=building_id).all()
    
    categories_data = []
    for cat in categories:
        # Get usage statistics
        usage_count = Expense.query.filter_by(category_id=cat.id).count()
        last_expense = Expense.query.filter_by(category_id=cat.id).order_by(desc(Expense.created_at)).first()
        
        categories_data.append({
            'id': cat.id,
            'code': cat.code,
            'name': cat.name,
            'description': cat.description,
            'allocation_method': cat.allocation_method.value,
            'is_active': cat.is_active,
            'building_id': cat.building_id,
            'settings': cat.settings or {},
            'usage_count': usage_count,
            'last_used': last_expense.period.strftime('%Y-%m-%d') if last_expense else None
        })
    
    return jsonify({'categories': categories_data})


@bp.route('/api/categories', methods=['POST'])
@login_required
def api_create_category():
    """Create new expense category"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['building_id', 'code', 'name', 'allocation_method']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Check building access
        building_id = data['building_id']
        if not current_user.is_superuser:
            has_access = db.session.query(Membership).join(Unit).filter(
                and_(
                    Unit.building_id == building_id,
                    Membership.user_id == current_user.id,
                    Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                )
            ).first()
            if not has_access:
                return jsonify({'success': False, 'error': 'Access denied to this building'}), 403
        
        # Check if code is unique in building
        existing = ExpenseCategory.query.filter_by(
            building_id=building_id, 
            code=data['code']
        ).first()
        if existing:
            return jsonify({'success': False, 'error': 'Category code already exists in this building'}), 400
        
        # Validate allocation method
        try:
            allocation_method = AllocationMethodEnum(data['allocation_method'])
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid allocation method'}), 400
        
        # Create category
        category = ExpenseCategory(
            building_id=building_id,
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            allocation_method=allocation_method,
            is_active=data.get('is_active', True),
            settings=data.get('settings', {})
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'category_id': category.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def api_update_category(category_id):
    """Update expense category"""
    try:
        category = ExpenseCategory.query.get_or_404(category_id)
        
        # Check building access
        if not current_user.is_superuser:
            has_access = db.session.query(Membership).join(Unit).filter(
                and_(
                    Unit.building_id == category.building_id,
                    Membership.user_id == current_user.id,
                    Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                )
            ).first()
            if not has_access:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'code' in data:
            # Check uniqueness
            existing = ExpenseCategory.query.filter_by(
                building_id=category.building_id, 
                code=data['code']
            ).filter(ExpenseCategory.id != category_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Category code already exists'}), 400
            category.code = data['code']
        
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'allocation_method' in data:
            try:
                category.allocation_method = AllocationMethodEnum(data['allocation_method'])
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid allocation method'}), 400
        if 'is_active' in data:
            category.is_active = data['is_active']
        if 'settings' in data:
            category.settings = data['settings']
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def api_delete_category(category_id):
    """Delete expense category"""
    try:
        category = ExpenseCategory.query.get_or_404(category_id)
        
        # Check building access
        if not current_user.is_superuser:
            has_access = db.session.query(Membership).join(Unit).filter(
                and_(
                    Unit.building_id == category.building_id,
                    Membership.user_id == current_user.id,
                    Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                )
            ).first()
            if not has_access:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if category is used in expenses
        expense_count = Expense.query.filter_by(category_id=category_id).count()
        if expense_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete category. It is used in {expense_count} expenses.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/categories/import', methods=['POST'])
@login_required
def api_import_categories():
    """Import categories from another building or standard templates"""
    try:
        data = request.get_json()
        method = data.get('method')
        building_id = data.get('building_id')
        
        if not building_id:
            return jsonify({'success': False, 'error': 'Building ID required'}), 400
        
        # Check building access
        if not current_user.is_superuser:
            has_access = db.session.query(Membership).join(Unit).filter(
                and_(
                    Unit.building_id == building_id,
                    Membership.user_id == current_user.id,
                    Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER])
                )
            ).first()
            if not has_access:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        imported_count = 0
        
        if method == 'template':
            source_building_id = data.get('source_building_id')
            if not source_building_id:
                return jsonify({'success': False, 'error': 'Source building ID required'}), 400
            
            # Copy categories from source building
            source_categories = ExpenseCategory.query.filter_by(building_id=source_building_id).all()
            
            for src_cat in source_categories:
                # Check if code already exists
                existing = ExpenseCategory.query.filter_by(
                    building_id=building_id,
                    code=src_cat.code
                ).first()
                
                if not existing:
                    new_category = ExpenseCategory(
                        building_id=building_id,
                        code=src_cat.code,
                        name=src_cat.name,
                        description=src_cat.description,
                        allocation_method=src_cat.allocation_method,
                        is_active=True,
                        settings=src_cat.settings or {}
                    )
                    db.session.add(new_category)
                    imported_count += 1
        
        elif method == 'standard':
            # Standard categories for residential buildings
            standard_categories = [
                {
                    'code': 'cleaning',
                    'name': 'Почистване',
                    'description': 'Почистване на общи части',
                    'allocation_method': AllocationMethodEnum.PER_UNIT
                },
                {
                    'code': 'lift',
                    'name': 'Лифт',
                    'description': 'Поддръжка на лифт',
                    'allocation_method': AllocationMethodEnum.PER_UNIT
                },
                {
                    'code': 'repairs',
                    'name': 'Ремонти',
                    'description': 'Ремонти на общи части',
                    'allocation_method': AllocationMethodEnum.SHARES
                },
                {
                    'code': 'landscaping',
                    'name': 'Озеленяване',
                    'description': 'Поддръжка на зелени площи',
                    'allocation_method': AllocationMethodEnum.SHARES
                },
                {
                    'code': 'security',
                    'name': 'Охрана',
                    'description': 'Охрана на сградата',
                    'allocation_method': AllocationMethodEnum.SHARES
                },
                {
                    'code': 'water',
                    'name': 'Вода',
                    'description': 'Разходи за вода',
                    'allocation_method': AllocationMethodEnum.METERED
                },
                {
                    'code': 'electricity',
                    'name': 'Ток',
                    'description': 'Разходи за електричество',
                    'allocation_method': AllocationMethodEnum.METERED
                }
            ]
            
            for std_cat in standard_categories:
                # Check if code already exists
                existing = ExpenseCategory.query.filter_by(
                    building_id=building_id,
                    code=std_cat['code']
                ).first()
                
                if not existing:
                    new_category = ExpenseCategory(
                        building_id=building_id,
                        code=std_cat['code'],
                        name=std_cat['name'],
                        description=std_cat['description'],
                        allocation_method=std_cat['allocation_method'],
                        is_active=True,
                        settings={}
                    )
                    db.session.add(new_category)
                    imported_count += 1
        
        else:
            return jsonify({'success': False, 'error': 'Invalid import method'}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'imported_count': imported_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/recent-expenses/<int:building_id>')
@login_required
def api_recent_expenses(building_id):
    """Get recent expenses for a building"""
    # Check building access
    if not current_user.is_superuser:
        has_access = db.session.query(Membership).join(Unit).filter(
            and_(
                Unit.building_id == building_id,
                Membership.user_id == current_user.id,
                Membership.role.in_([LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER, LocalRoleEnum.OWNER])
            )
        ).first()
        if not has_access:
            return jsonify({'expenses': []}), 403
    
    # Get recent expenses
    recent_expenses = db.session.query(Expense)\
        .options(joinedload(Expense.category))\
        .filter_by(building_id=building_id)\
        .order_by(desc(Expense.period))\
        .limit(10).all()
    
    expenses_data = []
    for expense in recent_expenses:
        expenses_data.append({
            'id': expense.id,
            'category_name': expense.category.name,
            'period': expense.period.strftime('%Y-%m'),
            'amount_total': float(expense.amount_total),
            'description': expense.description
        })
    
    return jsonify({'expenses': expenses_data})