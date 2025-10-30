"""
System models - Announcements, Access Control, Audit Logs, and Subscriptions
Based on the ER specification from copilot-instructions.md
"""

from app import db
from app.models import BaseModel, AuditMixin
from sqlalchemy.dialects.postgresql import JSONB, ENUM, INET
from sqlalchemy import Index, CheckConstraint, func, text
from datetime import datetime, date
import enum

class AccessTokenTypeEnum(enum.Enum):
    """Types of access tokens"""
    RFID = 'rfid'
    NFC = 'nfc'
    BLE = 'ble'
    QR = 'qr'
    MOBILE = 'mobile'

class AccessResultEnum(enum.Enum):
    """Access attempt results"""
    GRANTED = 'granted'
    DENIED = 'denied'
    ERROR = 'error'

class SubscriptionPlanEnum(enum.Enum):
    """Subscription plans"""
    FREE = 'free'
    STANDARD = 'standard'
    PRO = 'pro'
    ENTERPRISE = 'enterprise'

class SubscriptionStatusEnum(enum.Enum):
    """Subscription status"""
    ACTIVE = 'active'
    EXPIRED = 'expired'
    SUSPENDED = 'suspended'
    CANCELLED = 'cancelled'

class Announcement(BaseModel, AuditMixin):
    """Announcements and notices for buildings"""
    __tablename__ = 'announcements'
    
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    author_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    
    # Announcement content
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    
    # Visibility settings
    visible_from = db.Column(db.Date, default=func.current_date())
    visible_until = db.Column(db.Date)
    
    # Audience targeting (JSONB for flexibility)
    audience = db.Column(JSONB, default=dict)  # {entrances: ["A"], floors: [1,2], roles: ["owner"]}
    
    # Announcement properties
    is_urgent = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)
    
    # Engagement tracking
    views_count = db.Column(db.Integer, default=0)
    
    # Relationships
    building = db.relationship('Building', back_populates='announcements')
    author = db.relationship('User')
    
    # Constraints
    __table_args__ = (
        Index('idx_announcement_building', 'building_id'),
        Index('idx_announcement_visible', 'visible_from', 'visible_until'),
        Index('idx_announcement_published', 'is_published'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.audience:
            self.audience = {
                'entrances': [],  # Empty = all entrances
                'floors': [],     # Empty = all floors
                'roles': [],      # Empty = all roles
                'units': []       # Specific unit IDs
            }
    
    def is_visible_to_user(self, user, unit=None):
        """Check if announcement is visible to specific user"""
        from app.models.user import LocalRoleEnum
        
        # Check date range
        today = date.today()
        if self.visible_from and today < self.visible_from:
            return False
        if self.visible_until and today > self.visible_until:
            return False
        
        if not self.is_published:
            return False
        
        # Check audience targeting
        if not self.audience:
            return True  # No restrictions
        
        # Get user's memberships in this building
        user_memberships = [m for m in user.memberships 
                           if m.unit.building_id == self.building_id and m.is_active]
        
        if not user_memberships:
            return False  # User not in building
        
        # Check entrance filter
        if self.audience.get('entrances'):
            user_entrances = [m.unit.entrance for m in user_memberships]
            if not any(ent in self.audience['entrances'] for ent in user_entrances):
                return False
        
        # Check floor filter
        if self.audience.get('floors'):
            user_floors = [m.unit.floor for m in user_memberships]
            if not any(floor in self.audience['floors'] for floor in user_floors):
                return False
        
        # Check role filter
        if self.audience.get('roles'):
            user_roles = [m.role.value for m in user_memberships]
            if not any(role in self.audience['roles'] for role in user_roles):
                return False
        
        # Check specific units
        if self.audience.get('units'):
            user_unit_ids = [m.unit_id for m in user_memberships]
            if not any(unit_id in self.audience['units'] for unit_id in user_unit_ids):
                return False
        
        return True
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        db.session.commit()
    
    @property
    def is_current(self):
        """Check if announcement is currently visible"""
        today = date.today()
        return (
            self.is_published and
            (not self.visible_from or today >= self.visible_from) and
            (not self.visible_until or today <= self.visible_until)
        )
    
    def __repr__(self):
        return f'<Announcement {self.title[:30]}>'

class AccessToken(BaseModel, AuditMixin):
    """Access tokens for building entry (RFID, NFC, mobile keys, etc.)"""
    __tablename__ = 'access_tokens'
    
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    
    # Token details
    type = db.Column(ENUM(AccessTokenTypeEnum), nullable=False)
    token = db.Column(db.String(200), unique=True, nullable=False)
    
    # Token properties
    name = db.Column(db.String(100))  # User-friendly name
    description = db.Column(db.Text)
    
    # Validity period
    valid_from = db.Column(db.DateTime(timezone=True), default=func.now())
    valid_until = db.Column(db.DateTime(timezone=True))
    
    # Access zones and permissions
    zones = db.Column(JSONB, default=list)  # ["entrance_A", "garage", "common_areas"]
    permissions = db.Column(JSONB, default=dict)
    
    # Status
    enabled = db.Column(db.Boolean, default=True)
    is_temporary = db.Column(db.Boolean, default=False)
    
    # Usage tracking
    last_used_at = db.Column(db.DateTime(timezone=True))
    usage_count = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('User', back_populates='access_tokens')
    building = db.relationship('Building', back_populates='access_tokens')
    access_logs = db.relationship('AccessLog', back_populates='token', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        Index('idx_access_token_user', 'user_id'),
        Index('idx_access_token_building', 'building_id'),
        Index('idx_access_token_type', 'type'),
        Index('idx_access_token_enabled', 'enabled'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.zones:
            self.zones = ['main_entrance']  # Default zone
        
        if not self.permissions:
            self.permissions = {
                'time_windows': [],  # [{start: "08:00", end: "22:00", days: ["mon", "tue"]}]
                'max_uses_per_day': None,
                'guest_access': False
            }
    
    @property
    def is_valid(self):
        """Check if token is currently valid"""
        now = datetime.utcnow()
        
        if not self.enabled:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        return True
    
    def can_access_zone(self, zone, at_time=None):
        """Check if token can access specific zone at given time"""
        if not self.is_valid:
            return False
        
        if zone not in self.zones:
            return False
        
        # Check time windows if specified
        if at_time and self.permissions.get('time_windows'):
            # Time window validation logic would go here
            pass
        
        return True
    
    def record_usage(self, zone, result):
        """Record token usage"""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
        
        # Create access log
        log = AccessLog(
            token_id=self.id,
            zone=zone,
            result=result,
            at=self.last_used_at
        )
        log.save()
        
        db.session.commit()
    
    def __repr__(self):
        return f'<AccessToken {self.type.value}:{self.token[:8]}...>'

class AccessLog(BaseModel):
    """Access attempt logs"""
    __tablename__ = 'access_logs'
    
    token_id = db.Column(db.BigInteger, db.ForeignKey('access_tokens.id'), nullable=True)
    
    # Access attempt details
    zone = db.Column(db.String(100), nullable=False)  # door, gate, elevator, etc.
    result = db.Column(ENUM(AccessResultEnum), nullable=False)
    at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Additional context
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    log_metadata = db.Column(JSONB, default=dict)
    
    # Relationship
    token = db.relationship('AccessToken', back_populates='access_logs')
    
    # Constraints
    __table_args__ = (
        Index('idx_access_log_token', 'token_id'),
        Index('idx_access_log_zone_time', 'zone', 'at'),
        Index('idx_access_log_result', 'result'),
        Index('idx_access_log_time', 'at'),
    )
    
    def __repr__(self):
        return f'<AccessLog {self.zone} {self.result.value} {self.at}>'

class Subscription(BaseModel, AuditMixin):
    """Building subscriptions for different feature tiers"""
    __tablename__ = 'subscriptions'
    
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    
    # Subscription details
    plan = db.Column(ENUM(SubscriptionPlanEnum), nullable=False, default=SubscriptionPlanEnum.FREE)
    status = db.Column(ENUM(SubscriptionStatusEnum), nullable=False, default=SubscriptionStatusEnum.ACTIVE)
    
    # Validity period
    valid_from = db.Column(db.Date, default=func.current_date())
    valid_until = db.Column(db.Date)
    
    # Usage tracking
    features_used = db.Column(JSONB, default=dict)
    usage_stats = db.Column(JSONB, default=dict)
    
    # Billing information
    billing_info = db.Column(JSONB, default=dict)
    
    # Relationship
    building = db.relationship('Building', back_populates='subscription')
    
    # Constraints
    __table_args__ = (
        Index('idx_subscription_building', 'building_id'),
        Index('idx_subscription_plan_status', 'plan', 'status'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.features_used:
            self.features_used = {
                'users_count': 0,
                'announcements_count': 0,
                'api_calls_count': 0
            }
        
        if not self.usage_stats:
            self.usage_stats = {
                'monthly_active_users': 0,
                'storage_used_mb': 0
            }
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        if self.status != SubscriptionStatusEnum.ACTIVE:
            return False
        
        if self.valid_until:
            from datetime import date
            return date.today() <= self.valid_until
        
        return True
    
    def get_feature_limits(self):
        """Get feature limits based on subscription plan"""
        limits = {
            SubscriptionPlanEnum.FREE: {
                'max_users': 10,
                'max_units': 20,
                'max_announcements_per_month': 5,
                'storage_mb': 100,
                'api_calls_per_day': 100,
                'features': ['basic_management', 'announcements']
            },
            SubscriptionPlanEnum.STANDARD: {
                'max_users': 100,
                'max_units': 200,
                'max_announcements_per_month': 50,
                'storage_mb': 1000,
                'api_calls_per_day': 1000,
                'features': ['basic_management', 'announcements', 'finance', 'voting']
            },
            SubscriptionPlanEnum.PRO: {
                'max_users': 500,
                'max_units': 1000,
                'max_announcements_per_month': 200,
                'storage_mb': 5000,
                'api_calls_per_day': 10000,
                'features': ['all_features', 'iot_integration', 'access_control']
            },
            SubscriptionPlanEnum.ENTERPRISE: {
                'max_users': -1,  # Unlimited
                'max_units': -1,
                'max_announcements_per_month': -1,
                'storage_mb': 50000,
                'api_calls_per_day': 100000,
                'features': ['all_features', 'custom_integrations', 'dedicated_support']
            }
        }
        
        return limits.get(self.plan, limits[SubscriptionPlanEnum.FREE])
    
    def can_use_feature(self, feature_name):
        """Check if subscription allows specific feature"""
        if not self.is_active:
            return False
        
        limits = self.get_feature_limits()
        allowed_features = limits.get('features', [])
        
        return 'all_features' in allowed_features or feature_name in allowed_features
    
    def check_usage_limit(self, limit_type, current_value=None):
        """Check if usage is within limits"""
        if not self.is_active:
            return False
        
        limits = self.get_feature_limits()
        max_value = limits.get(limit_type)
        
        if max_value == -1:  # Unlimited
            return True
        
        if current_value is None:
            current_value = self.usage_stats.get(limit_type, 0)
        
        return current_value < max_value
    
    def update_usage(self, usage_type, increment=1):
        """Update usage statistics"""
        if not self.usage_stats:
            self.usage_stats = {}
        
        current = self.usage_stats.get(usage_type, 0)
        self.usage_stats[usage_type] = current + increment
        db.session.commit()
    
    def __repr__(self):
        return f'<Subscription {self.building.name} {self.plan.value}>'

class AuditLog(BaseModel):
    """Audit logs for tracking changes and actions"""
    __tablename__ = 'audit_logs'
    
    actor_user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=True)
    
    # Action details
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, login, etc.
    entity = db.Column(db.String(100), nullable=False)  # User, Building, Invoice, etc.
    entity_id = db.Column(db.BigInteger)
    
    # Change tracking
    diff = db.Column(JSONB, default=dict)  # {field: {old: value, new: value}}
    
    # Context
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Additional metadata
    audit_metadata = db.Column(JSONB, default=dict)
    
    # Relationship
    actor = db.relationship('User', back_populates='audit_logs')
    
    # Constraints
    __table_args__ = (
        Index('idx_audit_log_actor', 'actor_user_id'),
        Index('idx_audit_log_entity', 'entity', 'entity_id'),
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_time', 'at'),
    )
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity}:{self.entity_id}>'