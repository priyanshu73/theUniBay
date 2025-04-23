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


@bp.route('/search')
def search():
    # 1. Get parameters from URL query string
    keyword = request.args.get('keyword', default='', type=str).strip()
    category_id_str = request.args.get('category', default='', type=str)
    min_price_str = request.args.get('min_price', default='', type=str)
    max_price_str = request.args.get('max_price', default='', type=str)
    condition = request.args.get('condition', default='', type=str)
    status = request.args.get('status', default='available', type=str) # Default to available

    # 2. Validate and Convert Parameters
    category_id = None
    if category_id_str.isdigit():
        try:
            category_id = int(category_id_str)
        except ValueError:
            category_id = None # Should not happen with isdigit, but safe

    min_price = None
    try:
        if min_price_str: min_price = float(min_price_str)
        # Ensure non-negative, allow 0
        if min_price is not None and min_price < 0: min_price = 0.0
    except ValueError:
        min_price = None # Ignore if not a valid float

    max_price = None
    try:
        if max_price_str: max_price = float(max_price_str)
        # Ensure non-negative, allow 0
        if max_price is not None and max_price < 0: max_price = 0.0
    except ValueError:
        max_price = None # Ignore if not a valid float

    # Ensure min_price <= max_price if both provided
    if min_price is not None and max_price is not None and min_price > max_price:
         min_price, max_price = max_price, min_price # Swap them

    # Validate condition against allowed choices (fetch from forms.py or define here)
    allowed_conditions = ['new', 'like_new', 'good', 'fair', 'poor']
    if condition not in allowed_conditions:
        condition = '' # Reset if invalid value passed

    # Validate status
    allowed_statuses = ['available', 'sold', 'all']
    if status not in allowed_statuses:
        status = 'available' # Default to available if invalid

    # 3. Determine if any filters were actively applied by the user
    filters_applied = False
    if keyword or category_id is not None or min_price is not None or max_price is not None or condition or status != 'available':
        filters_applied = True
    # Special case: if only status=available is set, treat as no filters applied for collapse logic
    if status == 'available' and not (keyword or category_id is not None or min_price is not None or max_price is not None or condition):
         filters_applied = False


    # 4. Prepare for DB Query
    db = get_db()
    products = []
    categories = []
    # Static list of condition choices for the template dropdown
    condition_choices = [
        ('new', 'New (unused)'),
        ('like_new', 'Like New (barely used)'),
        ('good', 'Good (some signs of use)'),
        ('fair', 'Fair (noticeable wear)'),
        ('poor', 'Poor (significant wear)')
    ]

    try:
        # 5. Fetch Categories for Dropdown (Always needed)
        categories = db.execute("SELECT id, name FROM categories ORDER BY name").fetchall()

        # 6. Build the SQL Query Dynamically
        base_query = """
            SELECT
                p.id, p.title, p.price, p.image_path, p.is_sold, p.date_posted,
                c.name as category_name, u.name as seller_name,
                (SELECT COUNT(*) FROM likes WHERE likes.product_id = p.id) AS like_count
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN users u ON p.seller_id = u.id
        """
        sql_conditions = [] # Store parts of the WHERE clause
        parameters = []     # Store corresponding values for placeholders

        # Apply Status Filter (most common base filter)
        if status == 'sold':
             sql_conditions.append("p.is_sold = 1")
        elif status == 'available':
             sql_conditions.append("p.is_sold = 0")
        # No condition needed if status is 'all'

        # Apply Keyword Filter
        if keyword:
            sql_conditions.append("(p.title LIKE ? OR p.description LIKE ?)")
            parameters.extend([f"%{keyword}%", f"%{keyword}%"])

        # Apply Category Filter
        if category_id is not None:
            sql_conditions.append("p.category_id = ?")
            parameters.append(category_id)

        # Apply Condition Filter
        if condition:
             sql_conditions.append("p.condition = ?")
             parameters.append(condition)

        # Apply Price Filters
        if min_price is not None:
            sql_conditions.append("p.price >= ?")
            parameters.append(min_price)
        if max_price is not None:
            sql_conditions.append("p.price <= ?")
            parameters.append(max_price)

        # Construct the final query string
        query = base_query
        if sql_conditions: # Check if the list is not empty
            query += " WHERE " + " AND ".join(sql_conditions)

        query += " ORDER BY p.date_posted DESC" # Add ordering

        print(f"DEBUG Search SQL: {query}") # Debug Print
        print(f"DEBUG Search Params: {parameters}") # Debug Print

        # 7. Execute the Query
        products = db.execute(query, parameters).fetchall()

        # 8. Fetch Liked Product IDs for current user
        user_liked_ids = set()
        if current_user.is_authenticated:
             try:
                 likes_data = db.execute('SELECT product_id FROM likes WHERE user_id = ?', (current_user.id,)).fetchall()
                 user_liked_ids = {row['product_id'] for row in likes_data}
             except sqlite3.Error as like_e:
                  print(f"Error fetching user likes during search: {like_e}")
                  # Non-critical, proceed without liked status if it fails

    except sqlite3.Error as e:
        print(f"Error during database operation in search: {e}")
        flash("An error occurred while searching for products. Please check the criteria and try again.", "danger")
        # Still try to render the page, but products list will be empty
        products = [] # Ensure products is empty list on error

    # 9. Prepare parameters passed back to the template (for pre-filling form)
    search_params = {
        'keyword': keyword,
        'category': category_id, # Pass integer ID
        'min_price': min_price_str, # Pass original string
        'max_price': max_price_str, # Pass original string
        'condition': condition,
        'status': status
    }

    # 10. Render the Template
    return render_template('search_results.html',
                           title='Search Results',
                           products=products,                 # List of found products
                           categories=categories,             # List of categories for dropdown
                           conditions=condition_choices,      # List of condition tuples for dropdown
                           search_params=search_params,       # Dict of params to pre-fill form
                           user_liked_ids=user_liked_ids,     # Set of IDs liked by current user
                           filters_applied=filters_applied)   # Boolean for collapsible form
# --- NEW: Stats Route (GROUP BY Example) ---
@bp.route('/stats')
def stats():
    query = """
        SELECT c.name, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id -- Join condition
        -- Optional: Filter counted products, e.g., WHERE p.is_sold = 0
        GROUP BY c.id, c.name  -- Group by unique category identifier and name
        ORDER BY product_count DESC, c.name; -- Order results meaningfully
    """
    db = get_db()
    category_counts = []
    try:
        category_counts = db.execute(query).fetchall()
    except sqlite3.Error as e:
        print(f"An error occurred fetching stats: {e}")
        flash("Could not retrieve statistics.", "danger")

    return render_template('stats.html', # You need to create this template
                           title='Marketplace Statistics',
                           category_counts=category_counts)
