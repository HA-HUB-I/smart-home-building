"""
Flask-Admin Views for WebPortal
Production-ready admin interface with role-based access control
"""

from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash, request
from app.models.user import User, Membership, GlobalRoleEnum, LocalRoleEnum
from app.models.building import Building, Unit, IntercomEndpoint
from app.models.finance import ExpenseCategory, Expense, ExpenseAllocation, Invoice, Payment, Meter, MeterReading
from app.models.system import Announcement, AccessToken, AccessLog, Subscription, AuditLog

class AdminModelView(ModelView):
    """Base admin model view with authentication and authorization"""
    
    def is_accessible(self):
        """Check if current user can access admin panel"""
        if not current_user.is_authenticated:
            return False
        
        # Only superadmin and staff can access admin panel
        return (current_user.is_superuser or 
                current_user.global_role in [GlobalRoleEnum.SUPERADMIN, GlobalRoleEnum.STAFF])
    
    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login if not accessible"""
        flash('You need admin privileges to access this page.', 'error')
        return redirect(url_for('auth.login', next=request.url))
    
    # Common column configurations
    column_exclude_list = ['password_hash', 'created_at', 'updated_at']
    column_display_pk = True
    page_size = 50
    can_view_details = True
    can_export = True

class UserModelView(AdminModelView):
    """User management view"""
    model = User
    column_list = ['email', 'first_name', 'last_name', 'is_active', 'is_superuser', 'created_at']
    column_searchable_list = ['email', 'first_name', 'last_name']
    column_filters = ['is_active', 'is_superuser', 'is_verified']
    
    # Only include the most basic fields to avoid ENUM issues
    form_columns = ['email', 'first_name', 'last_name', 'is_active']
    
    # Exclude all problematic fields completely
    form_excluded_columns = [
        'id', 'password_hash', 'created_at', 'updated_at', 'global_role', 
        'settings', 'memberships', 'access_tokens', 'audit_logs',
        'last_login', 'login_count', 'is_superuser', 'phone', 'is_verified'
    ]
    
    # Disable dangerous operations
    can_create = False
    can_delete = False
    can_edit = True
    
    def create_model(self, form):
        """Override create to handle special cases"""
        try:
            model = self.model()
            form.populate_obj(model)
            # Set default password if creating new user
            if not model.password_hash:
                model.set_password('changeme123')  # Default password
            # Set default global_role
            model.global_role = GlobalRoleEnum.RESIDENT
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(f'Failed to create record. {str(ex)}', 'error')
            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, True)

        return model

class BuildingModelView(AdminModelView):
    """Admin view for Building model"""
    column_list = ['id', 'name', 'is_active', 'created_at']
    column_searchable_list = ['name']
    column_filters = ['is_active', 'created_at']
    
    # Form configuration
    form_excluded_columns = ['units', 'expense_categories', 'expenses', 'announcements', 'access_tokens', 'subscription', 'created_at', 'updated_at']
    form_create_rules = ['name', 'address', 'entrances', 'is_active', 'settings', 'bank_accounts']
    form_edit_rules = ['name', 'address', 'entrances', 'is_active', 'settings', 'bank_accounts']
    
    # Help text for JSONB fields
    form_widget_args = {
        'address': {
            'placeholder': '{"street": "ул. Примерна", "number": "123", "city": "София", "postcode": "1000"}'
        },
        'entrances': {
            'placeholder': '["А", "Б", "В"]'
        },
        'settings': {
            'placeholder': '{"quiet_hours": {"start": "22:00", "end": "08:00"}}'
        },
        'bank_accounts': {
            'placeholder': '[{"iban": "BG80BNBG96611020345678", "bank_name": "Банка", "account_holder": "ЕС Блок 1"}]'
        }
    }

class UnitModelView(AdminModelView):
    """Admin view for Unit model"""
    column_list = ['id', 'building', 'entrance', 'floor', 'number', 'area_m2', 'shares', 'occupancy_count']
    column_searchable_list = ['number']
    column_filters = ['building_id', 'entrance', 'floor', 'is_active']
    
    # Form configuration
    form_excluded_columns = ['memberships', 'intercom_endpoints', 'meters', 'expense_allocations', 'invoices', 'payments', 'created_at', 'updated_at']
    form_create_rules = ['building', 'entrance', 'floor', 'number', 'area_m2', 'shares', 'occupancy_count', 'intercom_ext', 'is_active']
    form_edit_rules = ['building', 'entrance', 'floor', 'number', 'area_m2', 'shares', 'occupancy_count', 'intercom_ext', 'is_active']

class MembershipModelView(AdminModelView):
    """Admin view for Membership model"""
    column_list = ['id', 'user', 'unit', 'is_active', 'is_primary', 'since', 'until']
    column_filters = ['is_active', 'is_primary', 'since']
    
    # Only basic fields without ENUM
    form_columns = ['user', 'unit', 'is_active', 'is_primary', 'since', 'until']

class ExpenseModelView(AdminModelView):
    """Admin view for Expense model"""
    column_list = ['id', 'building', 'category', 'period', 'amount_total', 'is_allocated', 'created_at']
    column_filters = ['building_id', 'category_id', 'period', 'is_allocated']
    
    form_excluded_columns = ['allocations']

class InvoiceModelView(AdminModelView):
    """Admin view for Invoice model"""
    column_list = ['id', 'unit', 'period', 'amount_due', 'amount_paid', 'status', 'due_date']
    column_filters = ['status', 'period', 'due_date']
    column_editable_list = ['status']
    
    def _balance_formatter(view, context, model, name):
        return f"{model.balance_due:.2f}"
    
    column_formatters = {
        'balance_due': _balance_formatter
    }

class PaymentModelView(AdminModelView):
    """Admin view for Payment model"""
    column_list = ['id', 'unit', 'amount', 'method', 'paid_at', 'reference', 'is_confirmed']
    column_filters = ['method', 'paid_at', 'is_confirmed']
    column_editable_list = ['is_confirmed']

class AnnouncementModelView(AdminModelView):
    """Admin view for Announcement model"""
    column_list = ['id', 'building', 'title', 'is_published', 'is_urgent', 'visible_from', 'visible_until']
    column_searchable_list = ['title', 'body']
    column_filters = ['building_id', 'is_published', 'is_urgent', 'visible_from']
    column_editable_list = ['is_published', 'is_urgent']

class AccessTokenModelView(AdminModelView):
    """Admin view for Access Token model"""
    column_list = ['id', 'user', 'building', 'type', 'enabled', 'valid_from', 'valid_until', 'usage_count']
    column_filters = ['type', 'enabled', 'building_id']
    column_editable_list = ['enabled']
    
    form_excluded_columns = ['access_logs', 'token']  # Hide sensitive token

class SubscriptionModelView(AdminModelView):
    """Admin view for Subscription model"""
    column_list = ['id', 'building', 'plan', 'status', 'valid_from', 'valid_until']
    column_filters = ['plan', 'status']
    column_editable_list = ['status']

class AuditLogModelView(AdminModelView):
    """Admin view for Audit Logs - Read only"""
    can_create = False
    can_edit = False
    can_delete = False
    
    column_list = ['id', 'actor', 'action', 'entity', 'entity_id', 'at']
    column_filters = ['action', 'entity', 'at']
    column_searchable_list = ['action', 'entity']

class DashboardView(BaseView):
    """Custom dashboard view"""
    
    @expose('/')
    def index(self):
        """Admin dashboard with statistics"""
        if not self.is_accessible():
            return self.inaccessible_callback('dashboard')
        
        # Gather statistics
        stats = {
            'total_users': User.query.count(),
            'total_buildings': Building.query.count(),
            'total_units': Unit.query.count(),
            'active_memberships': Membership.query.filter_by(is_active=True).count(),
            'recent_payments': Payment.query.order_by(Payment.paid_at.desc()).limit(5).all(),
            'recent_announcements': Announcement.query.filter_by(is_published=True).order_by(Announcement.created_at.desc()).limit(5).all()
        }
        
        return self.render('admin/dashboard.html', **stats)
    
    def is_accessible(self):
        """Check access like other admin views"""
        if not current_user.is_authenticated:
            return False
        return (current_user.is_superuser or 
                current_user.global_role in [GlobalRoleEnum.SUPERADMIN, GlobalRoleEnum.STAFF])

def register_admin_views(admin, db):
    """Register all admin views with Flask-Admin"""
    
    # Add custom dashboard
    dashboard = DashboardView(name='Dashboard', endpoint='dashboard')
    admin.add_view(dashboard)
    
    # User Management
    user_view = UserModelView(User, db.session)
    user_view.name = 'Users'
    user_view.category = 'Users'
    admin.add_view(user_view)
    
    membership_view = MembershipModelView(Membership, db.session)
    membership_view.name = 'Memberships'
    membership_view.category = 'Users'
    admin.add_view(membership_view)
    
    # Building Management
    building_view = BuildingModelView(Building, db.session)
    building_view.name = 'Buildings'
    building_view.category = 'Buildings'
    admin.add_view(building_view)
    
    unit_view = UnitModelView(Unit, db.session)
    unit_view.name = 'Units' 
    unit_view.category = 'Buildings'
    admin.add_view(unit_view)
    
    # Financial Management
    expense_view = ExpenseModelView(Expense, db.session)
    expense_view.name = 'Expenses'
    expense_view.category = 'Finance'
    admin.add_view(expense_view)
    
    invoice_view = InvoiceModelView(Invoice, db.session)
    invoice_view.name = 'Invoices'
    invoice_view.category = 'Finance'
    admin.add_view(invoice_view)
    
    payment_view = PaymentModelView(Payment, db.session)
    payment_view.name = 'Payments'
    payment_view.category = 'Finance'
    admin.add_view(payment_view)
    
    # Communication
    announcement_view = AnnouncementModelView(Announcement, db.session)
    announcement_view.name = 'Announcements'
    announcement_view.category = 'Communication'
    admin.add_view(announcement_view)
    
    # Access Control
    access_token_view = AccessTokenModelView(AccessToken, db.session)
    access_token_view.name = 'Access Tokens'
    access_token_view.category = 'Access'
    admin.add_view(access_token_view)
    
    # System Management
    subscription_view = SubscriptionModelView(Subscription, db.session)
    subscription_view.name = 'Subscriptions'
    subscription_view.category = 'System'
    admin.add_view(subscription_view)
    
    audit_view = AuditLogModelView(AuditLog, db.session)
    audit_view.name = 'Audit Logs'
    audit_view.category = 'System'
    admin.add_view(audit_view)
    
    print("✅ Flask-Admin views registered successfully")