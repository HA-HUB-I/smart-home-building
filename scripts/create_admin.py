#!/usr/bin/env python3
"""
Default Administrator Creation Script
Creates a default admin user for WebPortal application.
"""

import os
import sys
import getpass
from werkzeug.security import generate_password_hash

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User

def create_default_admin():
    """Create default administrator account"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if admin already exists
            existing_admin = User.query.filter_by(email='admin@webportal.local').first()
            if existing_admin:
                print("ℹ️  Default admin user already exists!")
                print(f"   Email: admin@webportal.local")
                print(f"   ID: {existing_admin.id}")
                return True
            
            # Create default admin user
            admin_user = User(
                email='admin@webportal.local',
                password_hash=generate_password_hash('admin123'),
                is_superuser=True,
                is_active=True,
                is_verified=True,
                first_name='System',
                last_name='Administrator'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Default administrator created successfully!")
            print("   📧 Email: admin@webportal.local")
            print("   🔑 Password: admin123")
            print("   � Role: Superuser")
            print("")
            print("⚠️  IMPORTANT: Change the default password after first login!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            db.session.rollback()
            return False

def create_custom_admin():
    """Create custom administrator account"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating custom administrator account...")
            print("-" * 40)
            
            email = input("Email: ").strip()
            if not email or '@' not in email:
                print("❌ Valid email is required!")
                return False
            
            # Check if user already exists
            existing_user = User.query.filter(User.email == email).first()
            
            if existing_user:
                print(f"❌ User with email '{email}' already exists!")
                return False
            
            password = getpass.getpass("Password: ").strip()
            if len(password) < 6:
                print("❌ Password must be at least 6 characters long!")
                return False
            
            confirm_password = getpass.getpass("Confirm password: ").strip()
            if password != confirm_password:
                print("❌ Passwords do not match!")
                return False
            
            first_name = input("First name (optional): ").strip()
            last_name = input("Last name (optional): ").strip()
            
            # Create admin user
            admin_user = User(
                email=email,
                password_hash=generate_password_hash(password),
                is_superuser=True,
                is_active=True,
                is_verified=True,
                first_name=first_name or 'Admin',
                last_name=last_name or 'User'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Administrator created successfully!")
            print(f"   📧 Email: {email}")
            print("   � Role: Superuser")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            db.session.rollback()
            return False

def main():
    """Main function"""
    print("🔐 WebPortal Administrator Creation")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--custom':
        success = create_custom_admin()
    else:
        print("Creating default administrator account...")
        print("Use --custom flag for custom admin creation")
        print()
        success = create_default_admin()
    
    if success:
        print("\n🎉 Administrator setup completed!")
    else:
        print("\n💥 Administrator setup failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()