"""
Finance models - Expenses, Invoices, Payments, and Financial management
Based on the ER specification from copilot-instructions.md
"""

from app import db
from app.models import BaseModel, AuditMixin
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy import Index, CheckConstraint, func
from decimal import Decimal
from datetime import datetime, date
import enum

class AllocationMethodEnum(enum.Enum):
    """Methods for expense allocation"""
    SHARES = 'shares'  # By ideal parts
    PER_UNIT = 'per_unit'  # Equal per unit
    PER_PERSON = 'per_person'  # By number of occupants
    METERED = 'metered'  # By meter readings
    CUSTOM = 'custom'  # Custom allocation

class InvoiceStatusEnum(enum.Enum):
    """Invoice payment status"""
    UNPAID = 'unpaid'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'

class PaymentMethodEnum(enum.Enum):
    """Payment methods"""
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    CARD = 'card'
    ONLINE = 'online'
    OTHER = 'other'

class ExpenseCategory(BaseModel, AuditMixin):
    """Expense categories for building expenses"""
    __tablename__ = 'expense_categories'
    
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    
    # Category identification
    code = db.Column(db.String(50), nullable=False)  # cleaning, lift, repair, etc.
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Allocation method
    allocation_method = db.Column(ENUM(AllocationMethodEnum), 
                                 nullable=False, 
                                 default=AllocationMethodEnum.SHARES)
    
    # Category settings and formulas
    settings = db.Column(JSONB, default=dict)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    building = db.relationship('Building', back_populates='expense_categories')
    expenses = db.relationship('Expense', back_populates='category', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('building_id', 'code', name='unique_category_code_per_building'),
        Index('idx_expense_category_building', 'building_id'),
        Index('idx_expense_category_code', 'code'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.settings:
            self.settings = {
                'formula': {},
                'rates': {},
                'auto_generate': False,
                'notifications': True
            }
    
    def calculate_allocations(self, total_amount, period=None):
        """Calculate expense allocations for all units in building"""
        from app.models.building import Unit
        
        units = Unit.query.filter_by(building_id=self.building_id, is_active=True).all()
        allocations = {}
        
        if self.allocation_method == AllocationMethodEnum.SHARES:
            # Allocate by ideal parts
            total_shares = sum(unit.shares or Decimal('0') for unit in units)
            if total_shares > 0:
                for unit in units:
                    if unit.shares:
                        allocations[unit.id] = (unit.shares / total_shares) * Decimal(str(total_amount))
                    else:
                        allocations[unit.id] = Decimal('0')
        
        elif self.allocation_method == AllocationMethodEnum.PER_UNIT:
            # Equal allocation per unit
            if units:
                amount_per_unit = Decimal(str(total_amount)) / len(units)
                for unit in units:
                    allocations[unit.id] = amount_per_unit
        
        elif self.allocation_method == AllocationMethodEnum.PER_PERSON:
            # Allocate by number of occupants
            total_occupants = sum(unit.occupancy_count or 0 for unit in units)
            if total_occupants > 0:
                amount_per_person = Decimal(str(total_amount)) / total_occupants
                for unit in units:
                    allocations[unit.id] = amount_per_person * (unit.occupancy_count or 0)
        
        elif self.allocation_method == AllocationMethodEnum.METERED:
            # Allocate by meter readings (requires meter data)
            # This would need integration with meter readings
            for unit in units:
                allocations[unit.id] = Decimal('0')  # Placeholder
        
        else:  # CUSTOM
            # Custom allocation based on settings
            for unit in units:
                allocations[unit.id] = Decimal('0')  # Placeholder
        
        return allocations
    
    def __repr__(self):
        return f'<ExpenseCategory {self.code}>'

class Expense(BaseModel, AuditMixin):
    """Individual expenses for buildings"""
    __tablename__ = 'expenses'
    
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    category_id = db.Column(db.BigInteger, db.ForeignKey('expense_categories.id'), nullable=False)
    
    # Expense details
    period = db.Column(db.Date, nullable=False)  # Usually first day of month
    amount_total = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Description and documentation
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Expense metadata
    expense_metadata = db.Column(JSONB, default=dict)
    
    # Status
    is_allocated = db.Column(db.Boolean, default=False)
    is_invoiced = db.Column(db.Boolean, default=False)
    
    # Relationships
    building = db.relationship('Building', back_populates='expenses')
    category = db.relationship('ExpenseCategory', back_populates='expenses')
    allocations = db.relationship('ExpenseAllocation', back_populates='expense', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount_total >= 0', name='check_positive_amount'),
        Index('idx_expense_building_period', 'building_id', 'period'),
        Index('idx_expense_category', 'category_id'),
    )
    
    def generate_allocations(self):
        """Generate expense allocations for all units"""
        if self.is_allocated:
            return False  # Already allocated
        
        allocations = self.category.calculate_allocations(self.amount_total, self.period)
        
        for unit_id, amount in allocations.items():
            allocation = ExpenseAllocation(
                expense_id=self.id,
                unit_id=unit_id,
                amount=amount,
                formula_snapshot={
                    'method': self.category.allocation_method.value,
                    'total_amount': float(self.amount_total),
                    'calculation_date': datetime.utcnow().isoformat()
                }
            )
            allocation.save()
        
        self.is_allocated = True
        db.session.commit()
        return True
    
    def get_total_allocated(self):
        """Get total allocated amount"""
        return db.session.query(func.sum(ExpenseAllocation.amount)).filter_by(expense_id=self.id).scalar() or Decimal('0')
    
    def __repr__(self):
        return f'<Expense {self.category.code} {self.period} {self.amount_total}>'

class ExpenseAllocation(BaseModel):
    """Allocation of expenses to specific units"""
    __tablename__ = 'expense_allocations'
    
    expense_id = db.Column(db.BigInteger, db.ForeignKey('expenses.id'), nullable=False)
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=False)
    
    # Allocation amount
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Formula snapshot for audit purposes
    formula_snapshot = db.Column(JSONB, default=dict)
    
    # Relationships
    expense = db.relationship('Expense', back_populates='allocations')
    unit = db.relationship('Unit', back_populates='expense_allocations')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('expense_id', 'unit_id', name='unique_allocation_per_unit'),
        CheckConstraint('amount >= 0', name='check_positive_allocation'),
        Index('idx_allocation_expense', 'expense_id'),
        Index('idx_allocation_unit', 'unit_id'),
    )
    
    def __repr__(self):
        return f'<ExpenseAllocation {self.unit.full_number} {self.amount}>'

class Invoice(BaseModel, AuditMixin):
    """Invoices/bills sent to units"""
    __tablename__ = 'invoices'
    
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=False)
    
    # Invoice details
    period = db.Column(db.Date, nullable=False)
    amount_due = db.Column(db.Numeric(12, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(12, 2), default=0)
    
    # Due date and status
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(ENUM(InvoiceStatusEnum), default=InvoiceStatusEnum.UNPAID)
    
    # Invoice details breakdown
    details = db.Column(JSONB, default=dict)  # Breakdown of charges
    
    # Metadata
    invoice_number = db.Column(db.String(50), unique=True)
    
    # Relationships
    unit = db.relationship('Unit', back_populates='invoices')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount_due >= 0', name='check_positive_due'),
        CheckConstraint('amount_paid >= 0', name='check_positive_paid'),
        Index('idx_invoice_unit_period', 'unit_id', 'period'),
        Index('idx_invoice_status', 'status'),
        Index('idx_invoice_due_date', 'due_date'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.invoice_number:
            self.invoice_number = f"INV-{self.unit_id}-{self.period.strftime('%Y%m')}-{self.id}"
    
    @property
    def balance_due(self):
        """Get remaining balance"""
        return self.amount_due - self.amount_paid
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from datetime import date
        return self.due_date < date.today() and self.status not in [InvoiceStatusEnum.PAID, InvoiceStatusEnum.CANCELLED]
    
    def update_status(self):
        """Update invoice status based on payments"""
        if self.amount_paid >= self.amount_due:
            self.status = InvoiceStatusEnum.PAID
        elif self.amount_paid > 0:
            self.status = InvoiceStatusEnum.PARTIAL
        elif self.is_overdue:
            self.status = InvoiceStatusEnum.OVERDUE
        else:
            self.status = InvoiceStatusEnum.UNPAID
        
        db.session.commit()
    
    def add_late_fee(self, fee_amount):
        """Add late fee to invoice"""
        self.amount_due += Decimal(str(fee_amount))
        
        if not self.details:
            self.details = {}
        
        if 'late_fees' not in self.details:
            self.details['late_fees'] = []
        
        self.details['late_fees'].append({
            'amount': float(fee_amount),
            'date': datetime.utcnow().isoformat(),
            'reason': 'Late payment fee'
        })
        
        db.session.commit()
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class Payment(BaseModel, AuditMixin):
    """Payments made by units"""
    __tablename__ = 'payments'
    
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=False)
    invoice_id = db.Column(db.BigInteger, db.ForeignKey('invoices.id'), nullable=True)
    
    # Payment details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(ENUM(PaymentMethodEnum), default=PaymentMethodEnum.BANK_TRANSFER)
    
    # Payment timing
    paid_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Payment reference and notes
    reference = db.Column(db.String(200))  # Bank reference, receipt number, etc.
    notes = db.Column(db.Text)
    
    # Payment metadata
    payment_metadata = db.Column(JSONB, default=dict)
    
    # Status
    is_confirmed = db.Column(db.Boolean, default=True)
    
    # Relationships
    unit = db.relationship('Unit', back_populates='payments')
    invoice = db.relationship('Invoice', back_populates='payments')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_positive_payment'),
        Index('idx_payment_unit', 'unit_id'),
        Index('idx_payment_invoice', 'invoice_id'),
        Index('idx_payment_date', 'paid_at'),
    )
    
    def apply_to_invoice(self):
        """Apply payment to invoice and update status"""
        if self.invoice and self.is_confirmed:
            self.invoice.amount_paid += self.amount
            self.invoice.update_status()
            return True
        return False
    
    def __repr__(self):
        return f'<Payment {self.amount} by {self.unit.full_number}>'

class Meter(BaseModel, AuditMixin):
    """Utility meters for units"""
    __tablename__ = 'meters'
    
    unit_id = db.Column(db.BigInteger, db.ForeignKey('units.id'), nullable=True)  # NULL for common meters
    building_id = db.Column(db.BigInteger, db.ForeignKey('buildings.id'), nullable=False)
    
    # Meter identification
    type = db.Column(db.String(50), nullable=False)  # water, electricity, gas, heating
    serial_no = db.Column(db.String(100))
    location = db.Column(db.String(200))
    
    # Meter properties
    installed_at = db.Column(db.Date)
    settings = db.Column(JSONB, default=dict)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    unit = db.relationship('Unit', back_populates='meters')
    building = db.relationship('Building')
    readings = db.relationship('MeterReading', back_populates='meter', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        Index('idx_meter_unit', 'unit_id'),
        Index('idx_meter_building', 'building_id'),
        Index('idx_meter_type', 'type'),
    )
    
    def get_latest_reading(self):
        """Get most recent meter reading"""
        return MeterReading.query.filter_by(meter_id=self.id).order_by(MeterReading.reading_at.desc()).first()
    
    def __repr__(self):
        return f'<Meter {self.type} {self.serial_no}>'

class MeterReading(BaseModel):
    """Meter readings over time"""
    __tablename__ = 'meter_readings'
    
    meter_id = db.Column(db.BigInteger, db.ForeignKey('meters.id'), nullable=False)
    
    # Reading data
    reading_value = db.Column(db.Numeric(14, 4), nullable=False)
    reading_at = db.Column(db.DateTime(timezone=True), nullable=False)
    
    # Reading source
    source = db.Column(db.String(20), default='manual')  # manual, import, iot
    
    # Additional data
    notes = db.Column(db.Text)
    reading_metadata = db.Column(JSONB, default=dict)
    
    # Relationship
    meter = db.relationship('Meter', back_populates='readings')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('reading_value >= 0', name='check_positive_reading'),
        Index('idx_reading_meter_date', 'meter_id', 'reading_at'),
    )
    
    def __repr__(self):
        return f'<MeterReading {self.meter.type} {self.reading_value}>'