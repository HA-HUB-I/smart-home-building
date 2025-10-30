"""
User models - Users, Roles, and Authentication
Based on the ER specification from copilot-instructions.md
"""

from app import db
from app.models import BaseModel, AuditMixin
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy import Index
import enum

# Enums for user roles
class GlobalRoleEnum(enum.Enum):
    SUPERADMIN = 'superadmin'
    STAFF = 'staff'
    ACCOUNTANT = 'accountant'
    DEVELOPER = 'developer'
    RESIDENT = 'resident'

class LocalRoleEnum(enum.Enum):
    MANAGER = 'manager'
    CASHIER = 'cashier'
    OWNER = 'owner'
    TENANT = 'tenant'
    OCCUPANT = 'occupant'
    GUEST = 'guest'

class User(UserMixin, BaseModel, AuditMixin):
    """User model with multi-authentication support"""
    __tablename__ = 'users'
    
    email = db.Column(db.String(120), unique=True, index=True)
    phone = db.Column(db.String(20), unique=True, index=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    
    # User status and flags
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Profile information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    
    # Settings and preferences (JSONB for flexibility)
    settings = db.Column(JSONB, default=dict)
    
    # Authentication tracking
    last_login = db.Column(db.DateTime(timezone=True))
    login_count = db.Column(db.Integer, default=0)
    
    # Global role (single role per user)
    global_role = db.Column(ENUM(GlobalRoleEnum), default=GlobalRoleEnum.RESIDENT)
    
    # Relationships
    memberships = db.relationship('Membership', back_populates='user', cascade='all, delete-orphan')
    access_tokens = db.relationship('AccessToken', back_populates='user', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='actor', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_phone', 'phone'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_global_role', 'global_role'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.settings:
            self.settings = {
                'theme': 'light',
                'language': 'bg',
                'notifications': {
                    'email': True,
                    'push': True,
                    'telegram': False
                },
                'privacy': {
                    'show_phone': False,
                    'show_email': False
                }
            }
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email or self.phone or f"User {self.id}"
    
    def get_buildings(self):
        """Get all buildings where user has membership"""
        from app.models.building import Building
        return db.session.query(Building).join(
            'units'
        ).join(
            'memberships'
        ).filter(
            Membership.user_id == self.id,
            Membership.is_active == True
        ).distinct().all()
    
    def get_memberships_for_building(self, building_id):
        """Get user's memberships in specific building"""
        return [m for m in self.memberships 
                if m.unit.building_id == building_id and m.is_active]
    
    def has_role_in_building(self, building_id, role):
        """Check if user has specific role in building"""
        memberships = self.get_memberships_for_building(building_id)
        return any(m.role == role for m in memberships)
    
    def is_manager_of_building(self, building_id):
        """Check if user is manager of building"""
        return self.has_role_in_building(building_id, LocalRoleEnum.MANAGER)
    
    def is_owner_in_building(self, building_id):
        """Check if user is owner in building"""
        return self.has_role_in_building(building_id, LocalRoleEnum.OWNER)
    
    def can_access_building(self, building_id):
        """Check if user can access building"""
        if self.is_superuser or self.global_role in [GlobalRoleEnum.SUPERADMIN, GlobalRoleEnum.STAFF]:
            return True
        return bool(self.get_memberships_for_building(building_id))
    
    def has_role(self, role):
        """Check if user has a specific role globally or in any building"""
        # Check global roles
        if role in ['superadmin', 'admin']:
            return self.is_superuser or self.global_role in [GlobalRoleEnum.SUPERADMIN, GlobalRoleEnum.STAFF]
        
        # Check local roles in any building
        if role in ['manager', 'owner', 'tenant', 'occupant']:
            role_enum = getattr(LocalRoleEnum, role.upper(), None)
            if role_enum:
                return any(m.role == role_enum for m in self.memberships if m.is_active)
        
        return False
    
    def get_role_in_building(self, building):
        """Get user's role in a specific building"""
        if not building:
            return None
        
        # Find active membership in this building
        for membership in self.memberships:
            if (membership.is_active and 
                membership.unit and 
                membership.unit.building_id == building.id):
                return membership.role.value if membership.role else None
        
        return None
    
    def record_login(self):
        """Record user login"""
        from datetime import datetime
        self.last_login = datetime.utcnow()
        self.login_count += 1
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.email or self.phone}>'

class Membership(BaseModel, AuditMixin):
    """Membership model - relationship between User and Unit with roles"""
    __tablename__ = 'memberships'
    
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=False)
    
    # Role in the building/unit
    role = db.Column(ENUM(LocalRoleEnum), nullable=False, default=LocalRoleEnum.OCCUPANT)
    
    # Status and timing
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    since = db.Column(db.Date, nullable=False)
    until = db.Column(db.Date, nullable=True)
    
    # Access policies (JSONB for flexibility)
    policy = db.Column(JSONB, default=dict)
    
    # Relationships
    user = db.relationship('User', back_populates='memberships')
    unit = db.relationship('Unit', back_populates='memberships')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'unit_id', name='unique_user_unit'),
        Index('idx_membership_user', 'user_id'),
        Index('idx_membership_unit', 'unit_id'),
        Index('idx_membership_role', 'role'),
        Index('idx_membership_active', 'is_active'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.since:
            from datetime import date
            self.since = date.today()
        
        if not self.policy:
            self.policy = {
                'visibility': {
                    'building_docs': self.role in [LocalRoleEnum.OWNER, LocalRoleEnum.MANAGER],
                    'expenses_summary': self.role in [LocalRoleEnum.OWNER, LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER],
                    'own_invoices': True,
                    'announcements': True
                },
                'actions': {
                    'vote': self.role == LocalRoleEnum.OWNER,
                    'view_finance': self.role in [LocalRoleEnum.OWNER, LocalRoleEnum.MANAGER, LocalRoleEnum.CASHIER],
                    'manage_building': self.role == LocalRoleEnum.MANAGER
                },
                'rate_limits': {
                    'announcements_per_day': 5 if self.role == LocalRoleEnum.MANAGER else 1
                }
            }
    
    @property
    def building(self):
        """Get building through unit relationship"""
        return self.unit.building if self.unit else None
    
    def has_permission(self, permission_key):
        """Check if membership has specific permission"""
        keys = permission_key.split('.')
        current = self.policy
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False
        
        return bool(current)
    
    def update_policy(self, updates):
        """Update policy settings"""
        if not self.policy:
            self.policy = {}
        
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self.policy, updates)
        db.session.commit()
    
    def __repr__(self):
        return f'<Membership {self.user.email} -> {self.unit} ({self.role.value})>'