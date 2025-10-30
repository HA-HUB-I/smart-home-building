"""
Application entry point for WebPortal
Production-ready Flask application with PostgreSQL
"""

import os
from app import create_app, db
from app.models import user, building, finance, system

# Create Flask application
app = create_app(os.getenv('FLASK_CONFIG', 'production'))

@app.shell_context_processor
def make_shell_context():
    """Make models available in Flask shell"""
    return {
        'db': db,
        'User': user.User,
        'Membership': user.Membership,
        'Building': building.Building,
        'Unit': building.Unit,
        'IntercomEndpoint': building.IntercomEndpoint,
        'ExpenseCategory': finance.ExpenseCategory,
        'Expense': finance.Expense,
        'ExpenseAllocation': finance.ExpenseAllocation,
        'Invoice': finance.Invoice,
        'Payment': finance.Payment,
        'Meter': finance.Meter,
        'MeterReading': finance.MeterReading,
        'Announcement': system.Announcement,
        'AccessToken': system.AccessToken,
        'AccessLog': system.AccessLog,
        'Subscription': system.Subscription,
        'AuditLog': system.AuditLog
    }

@app.cli.command()
def init_db():
    """Initialize database with sample data"""
    db.create_all()
    
    # Create sample building
    from app.models.building import Building, Unit
    from app.models.user import User, Membership, GlobalRoleEnum, LocalRoleEnum
    from app.models.system import Subscription, SubscriptionPlanEnum
    
    # Create admin user (check if exists first)
    admin = User.query.filter_by(email='admin@webportal.local').first()
    if not admin:
        admin = User(
            email='admin@webportal.local',
            global_role=GlobalRoleEnum.SUPERADMIN,
            is_superuser=True,
            first_name='Admin',
            last_name='User'
        )
        admin.set_password('admin123')
        admin.save()
        print("Created admin user: admin@webportal.local / admin123")
    
    # Create sample building (check if exists first)
    building = Building.query.filter_by(name='Block 11, Entrance A').first()
    if not building:
        building = Building(
            name='Block 11, Entrance A',
            address={
                'street': 'Primerna Street',
                'number': '11',
                'city': 'Sofia',
                'postcode': '1000',
                'country': 'Bulgaria'
            },
            entrances=['A', 'B']
        )
        building.save()
        print("Created sample building: Block 11, Entrance A")
    
    # Create sample units
    unit1 = Unit(
        building_id=building.id,
        entrance='A',
        floor=1,
        number='1',
        area_m2=62.50,
        shares=0.0165
    )
    unit1.save()
    
    unit2 = Unit(
        building_id=building.id,
        entrance='A',
        floor=1,
        number='2',
        area_m2=54.20,
        shares=0.0141
    )
    unit2.save()
    
    # Create subscription
    subscription = Subscription(
        building_id=building.id,
        plan=SubscriptionPlanEnum.PRO
    )
    subscription.save()
    
    print("Database initialized with sample data!")

if __name__ == '__main__':
    import sys
    port = 5001
    
    # Check for command line arguments for port
    for arg in sys.argv:
        if arg.startswith('--port='):
            port = int(arg.split('=')[1])
    
    app.run(debug=True, host='0.0.0.0', port=port)