# app/auth.py
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import sqlite3

from .forms import RegistrationForm, LoginForm
from .models import User
from db.db import get_db # Import the get_db helper
from app import login_manager # Import login_manager from app factory __init__

# Create Blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    """Callback used by Flask-Login to reload the user object from the user ID stored in the session."""
    return User.get(user_id) # Use the static method from models.py

# --- Registration Route ---
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirect if already logged in

    form = RegistrationForm()
    if form.validate_on_submit():
        # Data validated by form (including .edu and email_exists checks)
        name = form.name.data
        email = form.email.data.lower() # Store email in lowercase
        # Hash the password
        hashed_password = generate_password_hash(form.password.data)

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                (name, email, hashed_password)
            )
            db.commit()
            user_id = cursor.lastrowid # Get the ID of the new user

            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        except sqlite3.IntegrityError:
            # This catches emails that might exist if validator failed or race condition
            db.rollback() # Rollback the transaction
            flash('Email address already exists. Please log in or use a different email.', 'danger')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
            print(f"DB Error on registration: {e}") # Log the error

    # If GET request or form validation failed
    return render_template('auth/register.html', title='Register', form=form)

# --- Login Route ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirect if already logged in

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data
        remember = form.remember.data # Remember me checkbox

        db = get_db()
        try:
            # Fetch user by email - only get necessary fields initially
            user_row = db.execute(
                'SELECT id, password_hash FROM users WHERE email = ?', (email,)
            ).fetchone()

            if user_row and check_password_hash(user_row['password_hash'], password):
                # Password matches! Fetch full user data to create User object
                full_user_row = db.execute(
                    'SELECT id, name, email, profile_info FROM users WHERE id = ?', (user_row['id'],)
                ).fetchone()

                if full_user_row:
                    # Create User object for Flask-Login
                    user_obj = User(id=full_user_row['id'], name=full_user_row['name'], email=full_user_row['email'], profile_info=full_user_row['profile_info'])
                    login_user(user_obj, remember=remember) # Log the user in

                    flash('Login successful!', 'success')
                    # Redirect to 'next' page if available, otherwise index
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.index'))
                else:
                     # Should not happen if initial query worked, but good practice
                    flash('Could not retrieve user data after login.', 'danger')

            else:
                flash('Login unsuccessful. Please check email and password.', 'danger')

        except sqlite3.Error as e:
            flash(f'An error occurred during login: {e}', 'danger')
            print(f"DB Error on login: {e}") # Log the error

    # If GET request or form validation failed
    return render_template('auth/login.html', title='Login', form=form)

# --- Logout Route ---
@bp.route('/logout')
@login_required # Ensure user is logged in to log out
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))