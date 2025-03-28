from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.database import db, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        # Check if user exists and password is correct
        if not user or not user.check_password(password):
            flash('Username atau password salah. Silakan coba lagi.', 'danger')
            return render_template('auth/login.html', hide_nav=True)
        
        # Log in user
        login_user(user, remember=remember)
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html', hide_nav=True)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate form data
        if not username or not email or not password:
            flash('Semua field harus diisi.', 'danger')
            return render_template('auth/register.html', hide_nav=True)
            
        if password != confirm_password:
            flash('Password tidak cocok.', 'danger')
            return render_template('auth/register.html', hide_nav=True)
            
        # Check if username or email already exists
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        
        if user_exists:
            flash('Username telah digunakan. Silakan pilih username lain.', 'danger')
            return render_template('auth/register.html', hide_nav=True)
            
        if email_exists:
            flash('Email telah terdaftar. Silakan gunakan email lain.', 'danger')
            return render_template('auth/register.html', hide_nav=True)
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', hide_nav=True)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('auth.login'))