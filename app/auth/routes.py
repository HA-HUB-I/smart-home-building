"""
Auth routes for WebPortal
Authentication, login, logout, registration
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user import User
from . import bp

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login form and processing"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        if not email or not password:
            flash('Моля въведете имейл и парола', 'error')
            return render_template('auth/login.html')
        
        # Find user by email
        user = User.query.filter_by(email=email.lower()).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember_me)
            flash(f'Добре дошли, {user.email}!', 'success')
            
            # Redirect to next page or main index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Грешен имейл или парола', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    user_email = current_user.email
    logout_user()
    flash(f'Излязохте от системата. Довиждане!', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)