"""
Base model classes and database utilities
"""

from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.sql import func
from flask_login import UserMixin
import uuid
from datetime import datetime

class BaseModel(db.Model):
    """Base model with common fields for all models"""
    __abstract__ = True
    
    id = db.Column(db.BigInteger, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), 
                          server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), 
                          server_default=func.now(), 
                          onupdate=func.now(), nullable=False)
    
    def save(self):
        """Save the instance to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete the instance from database"""
        db.session.delete(self)
        db.session.commit()
    
    def to_dict(self, include_relationships=False):
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value
        
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                related = getattr(self, relationship.key)
                if related is not None:
                    if relationship.uselist:
                        result[relationship.key] = [item.to_dict() for item in related]
                    else:
                        result[relationship.key] = related.to_dict()
        
        return result

class AuditMixin:
    """Mixin for audit functionality"""
    
    def create_audit_log(self, action, actor_user_id, old_values=None, new_values=None):
        """Create audit log entry"""
        from app.models.system import AuditLog
        
        diff = {}
        if old_values and new_values:
            for key, new_val in new_values.items():
                old_val = old_values.get(key)
                if old_val != new_val:
                    diff[key] = {'old': old_val, 'new': new_val}
        
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity=self.__class__.__name__,
            entity_id=self.id,
            diff=diff
        )
        audit_log.save()
        return audit_log