# app/routes.py
from flask import Blueprint, render_template, abort, flash # Add abort
from flask_login import login_required # Add login_required
import sqlite3
from db.db import get_db


bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    page_title = "Welcome!"
    # Fetch products later
    return render_template('base.html', title=page_title) # Render base for now

# --- Basic Profile View Route ---
@bp.route('/profile/<int:user_id>')
@login_required 
def profile(user_id):
    db = get_db()
    try:
        user_row = db.execute(
            'SELECT id, name, email, join_date, profile_info FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if user_row:
            # Pass the user_row directly (it behaves like a dictionary)
            return render_template('profile.html', title=f"{user_row['name']}'s Profile", user=user_row)
        else:
            abort(404) # User not found

    except sqlite3.Error as e:
        print(f"DB Error on profile view: {e}") # Log the error
        flash("Could not retrieve profile information.", "danger")
        abort(500) # Internal server error