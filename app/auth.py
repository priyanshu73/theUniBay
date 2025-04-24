# app/auth.py
from datetime import datetime
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import sqlite3

from .forms import EditProfileForm, RegistrationForm, LoginForm
from .models import User
from db.db import get_db
from app import login_manager

bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data.lower()
        hashed_password = generate_password_hash(form.password.data)

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                (name, email, hashed_password)
            )
            db.commit()
            user_id = cursor.lastrowid

            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        except sqlite3.IntegrityError:
            db.rollback()
            flash('Email address already exists. Please log in or use a different email.', 'danger')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
            print(f"DB Error on registration: {e}")

    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data
        remember = form.remember.data

        db = get_db()
        try:
            user_row = db.execute(
                'SELECT id, password_hash FROM users WHERE email = ?', (email,)
            ).fetchone()

            if user_row and check_password_hash(user_row['password_hash'], password):
                full_user_row = db.execute(
                    'SELECT id, name, email, profile_info FROM users WHERE id = ?', (user_row['id'],)
                ).fetchone()

                if full_user_row:
                    user_obj = User(id=full_user_row['id'], name=full_user_row['name'], email=full_user_row['email'], profile_info=full_user_row['profile_info'])
                    login_user(user_obj, remember=remember)

                    flash('Login successful!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.index'))
                else:
                    flash('Could not retrieve user data after login.', 'danger')

            else:
                flash('Login unsuccessful. Please check email and password.', 'danger')

        except sqlite3.Error as e:
            flash(f'An error occurred during login: {e}', 'danger')
            print(f"DB Error on login: {e}")

    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db = get_db()
    form = EditProfileForm()

    # Fetch campuses for the dropdown
    campuses = db.execute(
        'SELECT id, name FROM campuses ORDER BY name'
    ).fetchall()
    # Add a 'None' option or similar if campus is optional
    form.campus_id.choices = [(0, '-- Select Campus --')] + [(campus['id'], campus['name']) for campus in campuses]

    if request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.profile_info.data = current_user.profile_info
        # Set default value for select field correctly
        form.campus_id.data = current_user.campus_id if current_user.campus_id else 0

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data.lower()
        profile_info = form.profile_info.data
        # Handle the 'None' option for campus
        campus_id = form.campus_id.data if form.campus_id.data != 0 else None

        try:
            db.execute(
                'UPDATE users SET name = ?, email = ?, profile_info = ?, campus_id = ? WHERE id = ?',
                (name, email, profile_info, campus_id, current_user.id)
            )
            db.commit()

            current_user.name = name
            current_user.email = email
            current_user.profile_info = profile_info
            current_user.campus_id = campus_id
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('main.profile', user_id=current_user.id))

        except sqlite3.IntegrityError:
            db.rollback()
            flash('The email address is already in use. Please use a different email.', 'danger')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'An error occurred while updating your profile: {e}', 'danger')
            print(f"DB Error on profile update: {e}")

    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)


@bp.route('/leave_review/<int:reviewed_user_id>', methods=['POST'])
@login_required
def leave_review(reviewed_user_id):
    db = get_db()
    text = request.form.get('text')
    rating = request.form.get('rating')

    if not text or not text.strip():
        flash('Review text cannot be empty.', 'warning')
        return redirect(url_for('main.profile', user_id=reviewed_user_id))
    if not rating:
        flash('Rating is required.', 'warning')
        return redirect(url_for('main.profile', user_id=reviewed_user_id))
    try:
        rating_int = int(rating)
        if not 1 <= rating_int <= 5:
             raise ValueError("Rating out of range")
    except ValueError:
         flash('Invalid rating value.', 'warning')
         return redirect(url_for('main.profile', user_id=reviewed_user_id))
    if current_user.id == reviewed_user_id:
        flash('You cannot review yourself.', 'warning')
        return redirect(url_for('main.profile', user_id=reviewed_user_id))

    try:
        db.execute(
            '''
            INSERT INTO reviews (reviewer_id, reviewed_user_id, comment, rating, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (current_user.id, reviewed_user_id, text.strip(), rating_int,datetime.now())
        )
        db.commit()
        flash('Your review has been submitted!', 'success')
    except sqlite3.Error as e:
        db.rollback()
        flash(f'An error occurred while submitting your review: {e}', 'danger')
        print(f"DB Error on review submission: {e}")

    return redirect(url_for('main.profile', user_id=reviewed_user_id, _anchor='reviews'))

@bp.route('/delete_profile', methods=['POST'])
@login_required
def delete_profile():
    db = get_db()
    try:
        db.execute('DELETE FROM users WHERE id = ?', (current_user.id,))
        db.commit()

        logout_user()
        flash('Your profile has been deleted successfully.', 'success')
        return redirect(url_for('main.index'))
    except sqlite3.Error as e:
        db.rollback()
        flash(f'An error occurred while deleting your profile: {e}', 'danger')
        print(f"DB Error on profile deletion: {e}")
        # Redirect to index if profile doesn't exist anymore
        return redirect(url_for('main.index'))