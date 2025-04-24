# app/routes.py
from datetime import datetime
from flask import Blueprint, redirect, render_template, abort, flash, request, url_for
from flask_login import current_user, login_required
import sqlite3
from db.db import get_db

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    db = get_db()
    user_liked_ids = set()

    if current_user.is_authenticated:
        try:
            likes_data = db.execute(
                'SELECT product_id FROM likes WHERE user_id = ?',
                (current_user.id,)
            ).fetchall()
            user_liked_ids = {row['product_id'] for row in likes_data}
        except sqlite3.Error as e:
             print(f"DB Error fetching user likes: {e}")
             flash("Could not load your liked items status.", "warning")

    try:
        products = db.execute(
            '''
            SELECT
                p.id, p.title, p.price, p.image_path, p.is_sold, p.date_posted,
                u.name AS seller_name,
                c.name AS category_name,
                (SELECT COUNT(*) FROM likes WHERE likes.product_id = p.id) AS like_count
            FROM products p
            JOIN users u ON p.seller_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_sold = 0
            ORDER BY p.date_posted DESC
            LIMIT 24
            '''
        ).fetchall()
        return render_template('index.html', title="Home", products=products, user_liked_ids=user_liked_ids)
    except sqlite3.Error as e:
        print(f"DB Error fetching index products: {e}")
        flash("Could not retrieve products.", "danger")
        return render_template('index.html', title="Home", products=[], user_liked_ids=user_liked_ids)


@bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    db = get_db()
    try:
        user_row = db.execute(
            '''
            SELECT
                u.id, u.name, u.email, u.join_date, u.profile_info,
                c.name AS campus_name
            FROM users u
            LEFT JOIN campuses c ON u.campus_id = c.id
            WHERE u.id = ?
            ''',
            (user_id,)
        ).fetchone()

        if not user_row:
            abort(404)

        user_products_rows = db.execute(
            '''
            SELECT id, title, price, is_sold, image_path
            FROM products
            WHERE seller_id = ?
            ORDER BY date_posted DESC
            ''',
            (user_id,)
        ).fetchall()

        reviews_rows = db.execute(
            '''
            SELECT
                r.comment,
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

        avg_rating_row = db.execute(
             "SELECT AVG(rating) as average_rating FROM reviews WHERE reviewed_user_id = ?",
             (user_id,)
         ).fetchone()
        avg_rating = avg_rating_row['average_rating'] if avg_rating_row and avg_rating_row['average_rating'] is not None else None

        return render_template(
            'profile.html',
            title=f"{user_row['name']}'s Profile",
            user=user_row,
            user_products=user_products_rows,
            reviews=reviews_rows,
            average_rating=avg_rating
        )

    except sqlite3.Error as e:
        print(f"DB Error on profile view (user_id: {user_id}): {e}")
        flash("Could not retrieve complete profile information.", "danger")
        abort(500)

@bp.route('/search')
def search():
    keyword = request.args.get('keyword', default='', type=str).strip()
    category_id_str = request.args.get('category', default='', type=str)
    min_price_str = request.args.get('min_price', default='', type=str)
    max_price_str = request.args.get('max_price', default='', type=str)
    condition = request.args.get('condition', default='', type=str)
    status = request.args.get('status', default='available', type=str)

    category_id = None
    if category_id_str.isdigit():
        try:
            category_id = int(category_id_str)
        except ValueError:
            category_id = None

    min_price = None
    try:
        if min_price_str: min_price = float(min_price_str)
        if min_price is not None and min_price < 0: min_price = 0.0
    except ValueError:
        min_price = None

    max_price = None
    try:
        if max_price_str: max_price = float(max_price_str)
        if max_price is not None and max_price < 0: max_price = 0.0
    except ValueError:
        max_price = None

    if min_price is not None and max_price is not None and min_price > max_price:
         min_price, max_price = max_price, min_price

    allowed_conditions = ['new', 'like_new', 'good', 'fair', 'poor']
    if condition not in allowed_conditions:
        condition = ''

    allowed_statuses = ['available', 'sold', 'all']
    if status not in allowed_statuses:
        status = 'available'

    filters_applied = False
    if keyword or category_id is not None or min_price is not None or max_price is not None or condition or status != 'available':
        filters_applied = True
    if status == 'available' and not (keyword or category_id is not None or min_price is not None or max_price is not None or condition):
         filters_applied = False


    db = get_db()
    products = []
    categories = []
    condition_choices = [
        ('new', 'New (unused)'),
        ('like_new', 'Like New (barely used)'),
        ('good', 'Good (some signs of use)'),
        ('fair', 'Fair (noticeable wear)'),
        ('poor', 'Poor (significant wear)')
    ]

    try:
        categories = db.execute("SELECT id, name FROM categories ORDER BY name").fetchall()

        base_query = """
            SELECT
                p.id, p.title, p.price, p.image_path, p.is_sold, p.date_posted,
                c.name as category_name, u.name as seller_name,
                (SELECT COUNT(*) FROM likes WHERE likes.product_id = p.id) AS like_count
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN users u ON p.seller_id = u.id
        """
        sql_conditions = []
        parameters = []

        if status == 'sold':
             sql_conditions.append("p.is_sold = 1")
        elif status == 'available':
             sql_conditions.append("p.is_sold = 0")

        if keyword:
            sql_conditions.append("(p.title LIKE ? OR p.description LIKE ?)")
            parameters.extend([f"%{keyword}%", f"%{keyword}%"])

        if category_id is not None:
            sql_conditions.append("p.category_id = ?")
            parameters.append(category_id)

        if condition:
             sql_conditions.append("p.condition = ?")
             parameters.append(condition)

        if min_price is not None:
            sql_conditions.append("p.price >= ?")
            parameters.append(min_price)
        if max_price is not None:
            sql_conditions.append("p.price <= ?")
            parameters.append(max_price)

        query = base_query
        if sql_conditions:
            query += " WHERE " + " AND ".join(sql_conditions)

        query += " ORDER BY p.date_posted DESC"

        # print(f"DEBUG Search SQL: {query}")
        # print(f"DEBUG Search Params: {parameters}")

        products = db.execute(query, parameters).fetchall()

        user_liked_ids = set()
        if current_user.is_authenticated:
             try:
                 likes_data = db.execute('SELECT product_id FROM likes WHERE user_id = ?', (current_user.id,)).fetchall()
                 user_liked_ids = {row['product_id'] for row in likes_data}
             except sqlite3.Error as like_e:
                  print(f"Error fetching user likes during search: {like_e}")

    except sqlite3.Error as e:
        print(f"Error during database operation in search: {e}")
        flash("An error occurred while searching for products. Please check the criteria and try again.", "danger")
        products = []

    search_params = {
        'keyword': keyword,
        'category': category_id,
        'min_price': min_price_str,
        'max_price': max_price_str,
        'condition': condition,
        'status': status
    }

    return render_template('search_results.html',
                           title='Search Results',
                           products=products,
                           categories=categories,
                           conditions=condition_choices,
                           search_params=search_params,
                           user_liked_ids=user_liked_ids,
                           filters_applied=filters_applied)

@bp.route('/stats')
def stats():
    query = """
        SELECT c.name, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id, c.name
        ORDER BY product_count DESC, c.name;
    """
    db = get_db()
    category_counts = []
    try:
        category_counts = db.execute(query).fetchall()
    except sqlite3.Error as e:
        print(f"An error occurred fetching stats: {e}")
        flash("Could not retrieve statistics.", "danger")

    return render_template('stats.html',
                           title='Marketplace Statistics',
                           category_counts=category_counts)