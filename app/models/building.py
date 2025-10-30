"""
Building models - Buildings, Units, and Property management
Based on the ER specification from copilot-instructions.md
"""

from app import db
from app.models import BaseModel, AuditMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index, CheckConstraint
from decimal import Decimal

class Building(BaseModel, AuditMixin):
    """Building model - represents a residential building or complex"""
    __tablename__ = 'buildings'
    
    name = db.Column(db.String(200), nullable=False)
    
    # Address stored as JSONB for flexibility
    address = db.Column(JSONB, nullable=False)  # {street, number, city, postcode, country}
    
    # Building configuration
    entrances = db.Column(JSONB, default=list)  # ["A", "B", "C"] or ["Вх.1", "Вх.2"]
    
    # Building settings and policies
    settings = db.Column(JSONB, default=dict)
    
    # Bank accounts for the building
    bank_accounts = db.Column(JSONB, default=list)
    
    # Building status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    units = db.relationship('Unit', back_populates='building', cascade='all, delete-orphan')
    expense_categories = db.relationship('ExpenseCategory', back_populates='building', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='building', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='building', cascade='all, delete-orphan')
    access_tokens = db.relationship('AccessToken', back_populates='building', cascade='all, delete-orphan')
    subscription = db.relationship('Subscription', back_populates='building', uselist=False, cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_building_name', 'name'),
        Index('idx_building_address', 'address', postgresql_using='gin'),
        Index('idx_building_active', 'is_active'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.settings:
            self.settings = {
                'charges': {
                    'late_fee_percentage': 0.1,  # 10% late fee
                    'due_day': 15,  # 15th of each month
                    'grace_period_days': 5
                },
                'voting': {
                    'quorum_percentage': 50,  # 50% for quorum
                    'majority_percentage': 50,  # Simple majority
                    'voting_period_days': 14
                },
                'notifications': {
                    'payment_reminders': True,
                    'maintenance_alerts': True,
                    'meeting_notifications': True
                },
                'access': {
                    'quiet_hours': {'start': '22:00', 'end': '07:00'},
                    'visitor_registration': True
                },
                'iot': {
                    'enabled': False,
                    'sensors': [],
                    'automation_rules': []
                }
            }
        
        if not isinstance(self.entrances, list):
            self.entrances = []
        
        if not isinstance(self.bank_accounts, list):
            self.bank_accounts = []
    
    @property
    def full_address(self):
        """Get formatted full address"""
        if not self.address:
            return ""
        
        parts = []
        if self.address.get('street'):
            parts.append(self.address['street'])
        if self.address.get('number'):
            parts.append(str(self.address['number']))
        if self.address.get('city'):
            parts.append(self.address['city'])
        
        return ', '.join(parts)
    
    def get_total_units(self):
        """Get total number of units in building"""
        return len(self.units)
    
    def get_units_by_entrance(self, entrance):
        """Get units in specific entrance"""
        return [unit for unit in self.units if unit.entrance == entrance]
    
    def get_total_area(self):
        """Get total area of all units"""
        return sum(unit.area_m2 or Decimal('0') for unit in self.units)
    
    def get_total_shares(self):
        """Get total ideal shares"""
        return sum(unit.shares or Decimal('0') for unit in self.units)
    
    def get_managers(self):
        """Get all managers of the building"""
        from app.models.user import User, Membership, LocalRoleEnum
        return db.session.query(User).join(
            Membership
        ).join(
            Unit
        ).filter(
            Unit.building_id == self.id,
            Membership.role == LocalRoleEnum.MANAGER,
            Membership.is_active == True
        ).distinct().all()
    
    def get_owners(self):
        """Get all owners in the building"""
        from app.models.user import User, Membership, LocalRoleEnum
        return db.session.query(User).join(
            Membership
        ).join(
            Unit
        ).filter(
            Unit.building_id == self.id,
            Membership.role == LocalRoleEnum.OWNER,
            Membership.is_active == True
        ).distinct().all()
    
    def add_entrance(self, entrance_name):
        """Add new entrance"""
        if not self.entrances:
            self.entrances = []
        if entrance_name not in self.entrances:
            self.entrances = self.entrances + [entrance_name]
            db.session.commit()
    
    def remove_entrance(self, entrance_name):
        """Remove entrance (only if no units use it)"""
        units_in_entrance = self.get_units_by_entrance(entrance_name)
        if not units_in_entrance and entrance_name in self.entrances:
            new_entrances = [e for e in self.entrances if e != entrance_name]
            self.entrances = new_entrances
            db.session.commit()
            return True
        return False
    
    def add_bank_account(self, iban, bank_name, account_holder):
        """Add bank account"""
        if not self.bank_accounts:
            self.bank_accounts = []
        
        account = {
            'iban': iban,
            'bank_name': bank_name,
            'account_holder': account_holder,
            'is_primary': len(self.bank_accounts) == 0
        }
        self.bank_accounts = self.bank_accounts + [account]
        db.session.commit()
    
    @property
    def active_memberships_count(self):
        """Count of active memberships in this building"""
        from app.models.user import Membership
        return db.session.query(Membership).join(Unit).filter(
            Unit.building_id == self.id,
            Membership.is_active == True
        ).count()
    
    @property
    def floors_count(self):
        """Count of unique floors in building"""
        floors = set()
        for unit in self.units:
            if unit.floor is not None:
                floors.add(unit.floor)
        return len(floors)

    def __repr__(self):
        return f'<Building {self.name}>'

class Unit(BaseModel, AuditMixin):
    """Unit model - represents an apartment, office, or property unit"""
    __tablename__ = 'units'
    
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    
    # Unit identification
    entrance = db.Column(db.String(10))  # A, B, C, Вх.1, etc.
    floor = db.Column(db.Integer)
    number = db.Column(db.String(20), nullable=False)  # Apartment number
    
    # Unit properties
    area_m2 = db.Column(db.Numeric(8, 2))  # Square meters
    shares = db.Column(db.Numeric(10, 6))  # Ideal parts/shares
    occupancy_count = db.Column(db.Integer, default=0)  # Number of occupants
    
    # Intercom and access
    intercom_ext = db.Column(db.String(20))  # Extension number
    
    # Unit settings
    settings = db.Column(JSONB, default=dict)
    
    # Unit status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    building = db.relationship('Building', back_populates='units')
    memberships = db.relationship('Membership', back_populates='unit', cascade='all, delete-orphan')
    intercom_endpoints = db.relationship('IntercomEndpoint', back_populates='unit', cascade='all, delete-orphan')
    meters = db.relationship('Meter', back_populates='unit', cascade='all, delete-orphan')
    expense_allocations = db.relationship('ExpenseAllocation', back_populates='unit', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='unit', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='unit', cascade='all, delete-orphan')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('building_id', 'entrance', 'number', name='unique_unit_in_building'),
        Index('idx_unit_building', 'building_id'),
        Index('idx_unit_entrance_floor', 'entrance', 'floor'),
        Index('idx_unit_number', 'number'),
        CheckConstraint('area_m2 >= 0', name='check_positive_area'),
        CheckConstraint('shares >= 0', name='check_positive_shares'),
        CheckConstraint('occupancy_count >= 0', name='check_positive_occupancy'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.settings:
            self.settings = {
                'notifications': {
                    'receive_announcements': True,
                    'payment_reminders': True
                },
                'privacy': {
                    'show_in_directory': True,
                    'allow_contact': True
                },
                'preferences': {
                    'preferred_contact_method': 'email'
                }
            }
    
    @property
    def full_number(self):
        """Get full unit identifier"""
        parts = []
        if self.entrance:
            parts.append(f"Вх. {self.entrance}")
        if self.floor is not None:
            parts.append(f"Ет. {self.floor}")
        parts.append(f"Ап. {self.number}")
        return ', '.join(parts)
    
    def get_active_memberships(self):
        """Get active memberships for this unit"""
        return [m for m in self.memberships if m.is_active]
    
    def get_owners(self):
        """Get owners of this unit"""
        from app.models.user import LocalRoleEnum
        return [m.user for m in self.get_active_memberships() 
                if m.role == LocalRoleEnum.OWNER]
    
    def get_tenants(self):
        """Get tenants of this unit"""
        from app.models.user import LocalRoleEnum
        return [m.user for m in self.get_active_memberships() 
                if m.role == LocalRoleEnum.TENANT]
    
    def get_all_occupants(self):
        """Get all occupants (owners, tenants, family members)"""
        return [m.user for m in self.get_active_memberships()]
    
    def get_primary_contact(self):
        """Get primary contact person for this unit"""
        primary_memberships = [m for m in self.get_active_memberships() if m.is_primary]
        if primary_memberships:
            return primary_memberships[0].user
        
        # Fallback to first owner, then first tenant
        owners = self.get_owners()
        if owners:
            return owners[0]
        
        tenants = self.get_tenants()
        if tenants:
            return tenants[0]
        
        # Fallback to any occupant
        occupants = self.get_all_occupants()
        return occupants[0] if occupants else None
    
    def calculate_share_percentage(self):
        """Calculate unit's percentage of total building shares"""
        if not self.shares or not self.building:
            return Decimal('0')
        
        total_shares = self.building.get_total_shares()
        if total_shares > 0:
            return (self.shares / total_shares) * 100
        return Decimal('0')
    
    def update_occupancy_count(self):
        """Update occupancy count based on active memberships"""
        self.occupancy_count = len(self.get_active_memberships())
        db.session.commit()
    
    def __repr__(self):
        return f'<Unit {self.full_number}>'

class IntercomEndpoint(BaseModel):
    """Intercom endpoint for unit communications"""
    __tablename__ = 'intercom_endpoints'
    
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=False)
    
    # Endpoint configuration
    type = db.Column(db.String(20), nullable=False)  # webrtc, sip, phone
    address = db.Column(db.String(200), nullable=False)  # sip:user@domain, tel:+359..., etc.
    display_name = db.Column(db.String(100))
    
    # Access control
    is_public = db.Column(db.Boolean, default=False)
    call_permissions = db.Column(JSONB, default=dict)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    unit = db.relationship('Unit', back_populates='intercom_endpoints')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("type IN ('webrtc', 'sip', 'phone')", name='check_endpoint_type'),
        Index('idx_intercom_unit', 'unit_id'),
        Index('idx_intercom_type', 'type'),
    )
    
    def __repr__(self):
        return f'<IntercomEndpoint {self.type}:{self.address}>'