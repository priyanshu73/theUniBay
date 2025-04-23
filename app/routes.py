# app/routes.py
from datetime import datetime
from flask import Blueprint, redirect, render_template, abort, flash, request, url_for
from flask_login import current_user, login_required
import sqlite3
from db.db import get_db # Make sure get_db is correctly imported

bp = Blueprint('main', __name__)

# --- index route ---
@bp.route('/')
@bp.route('/index')
def index():
    db = get_db()
    
    db = get_db()
    user_liked_ids = set() # Default empty set

    # If user is logged in, get their liked product IDs
    if current_user.is_authenticated:
        likes_data = db.execute(
            'SELECT product_id FROM likes WHERE user_id = ?',
            (current_user.id,)
        ).fetchall()
        user_liked_ids = {row['product_id'] for row in likes_data}
    try:
        products = db.execute(
            '''
            SELECT
                p.*,
                u.name AS seller_name,
                c.name AS category_name,
                p.image_path,
                (SELECT COUNT(*) FROM likes WHERE likes.product_id = p.id) AS like_count,
                (SELECT COUNT(*) FROM comments WHERE comments.product_id = p.id) AS comment_count
            FROM products p
            JOIN users u ON p.seller_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_sold = 0
            ORDER BY p.date_posted DESC
            '''
        ).fetchall()
        return render_template('index.html', title="All Products", products=products, user_liked_ids=user_liked_ids)
    except sqlite3.Error as e:
        print(f"DB Error: {e}")
        flash("Could not retrieve products.", "danger")
        return render_template('index.html', title="All Products", products=[])


# --- Updated Profile View Route ---
@bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    db = get_db()
    try:
        # 1. Fetch User Details
        user_row = db.execute(
            'SELECT id, name, email, join_date, profile_info FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if not user_row:
            abort(404)

        # 2. Fetch User's Listings
        user_products_rows = db.execute(
            '''
            SELECT id, title, price, is_sold
            FROM products
            WHERE seller_id = ?
            ORDER BY date_posted DESC
            ''',
            (user_id,)
        ).fetchall()

        # 3. Fetch Reviews ABOUT this User
        reviews_rows = db.execute(
            '''
            SELECT
                r.comment AS text, -- CORRECTED: Select 'comment' column, alias as 'text'
                r.rating,
                r.timestamp,
                u.name AS reviewer_name
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.id
            WHERE r.reviewed_user_id = ?
            ORDER BY r.timestamp DESC
            ''',
            (user_id,)
        ).fetchall()

        # 4. Pass all data to the template
        return render_template(
            'profile.html',
            title=f"",
            user=user_row,
            user_products=user_products_rows,
            reviews=reviews_rows
        )

    except sqlite3.Error as e:
        print(f"DB Error on profile view (user_id: {user_id}): {e}")
        flash("Could not retrieve complete profile information.", "danger")
        abort(500)


