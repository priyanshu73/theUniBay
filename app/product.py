# app/product.py
import os
from flask import (
    Blueprint, render_template, flash, redirect, url_for, request, current_app
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime

from .forms import ProductForm
from db.db import get_db

bp = Blueprint('product', __name__, url_prefix='/product')

def save_image(form_image):
    if not form_image.data:
        return None

    random_hex = os.urandom(8).hex()
    _, file_ext = os.path.splitext(form_image.data.filename)
    filename = random_hex + file_ext

    upload_dir = os.path.join(current_app.root_path, 'static', 'product_images')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_path = os.path.join(upload_dir, filename)
    form_image.data.save(file_path)

    return f'product_images/{filename}'

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ProductForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        price = float(form.price.data)
        category_id = form.category.data
        condition = form.condition.data

        image_path = save_image(form.image) if form.image.data else None
        print(f"title: {title}, description: {description}, price: {price}, category_id: {category_id}, condition: {condition}, image_path: {image_path}")
        print

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO products (title, description, price, category_id, condition, image_path, seller_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (title, description, price, category_id, condition, image_path, current_user.id)
            )
            db.commit()
            product_id = cursor.lastrowid

            flash('Your listing has been created!', 'success')
            return redirect(url_for('product.product_view', product_id=product_id))

        except sqlite3.Error as e:
            db.rollback()
            flash(f'An error occurred while creating your listing: {e}', 'danger')
            print(f"DB Error on product creation: {e}")

    return render_template('product/create.html', title='', form=form)

@bp.route('/<int:product_id>')
@login_required
def product_view(product_id):
    db = get_db()
    product = None
    comments = []
    user_liked = False

    try:
        product_data = db.execute(
            '''
            SELECT
                p.*,
                u.name AS seller_name,
                u.email AS seller_email,
                c.name AS category_name,
                (SELECT COUNT(*) FROM likes WHERE likes.product_id = p.id) AS like_count,
                (SELECT COUNT(*) FROM comments WHERE comments.product_id = p.id) AS comment_count
            FROM products p
            JOIN users u ON p.seller_id = u.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
            ''',
            (product_id,)
        ).fetchone()

        if product_data is None:
            flash("Product not found.", "warning")
            return redirect(url_for('main.index'))

        product = dict(product_data)

        comments_data = db.execute(
            '''
            SELECT
                com.text,
                com.timestamp,
                u.name AS commenter_name
            FROM comments com
            JOIN users u ON com.user_id = u.id
            WHERE com.product_id = ?
            ORDER BY com.timestamp DESC
            ''',
            (product_id,)
        ).fetchall()
        comments = [dict(row) for row in comments_data]

        if current_user.is_authenticated:
            like_exists = db.execute(
                'SELECT 1 FROM likes WHERE user_id = ? AND product_id = ? LIMIT 1',
                (current_user.id, product_id)
            ).fetchone()
            if like_exists:
                user_liked = True

        return render_template('product/view.html',
                               product=product,
                               comments=comments,
                               user_liked=user_liked)

    except sqlite3.Error as e:
        print(f"Database Error in product_view (product_id: {product_id}): {e}")
        flash("An error occurred while retrieving product details. Please try again.", "danger")
        return redirect(url_for('main.index'))

@bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    db = get_db()

    try:
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()

        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))

        if product['seller_id'] != current_user.id:
            flash('You do not have permission to edit this listing.', 'danger')
            return redirect(url_for('product.product_view', product_id=product_id))

        form = ProductForm()

        if request.method == 'GET':
            form.title.data = product['title']
            form.description.data = product['description']
            form.price.data = product['price']
            form.category.data = product['category_id']
            form.condition.data = product['condition']

        if form.validate_on_submit():
            title = form.title.data
            description = form.description.data
            price = float(form.price.data)
            category_id = form.category.data
            condition = form.condition.data

            if form.image.data:
                if product['image_path']:
                    old_image_path = os.path.join(current_app.root_path, 'static', product['image_path'])
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                image_path = save_image(form.image)
            else:
                image_path = product['image_path']

            db.execute(
                'UPDATE products SET title = ?, description = ?, price = ?, '
                'category_id = ?, condition = ?, image_path = ? WHERE id = ?',
                (title, description, price, category_id, condition, image_path, product_id)
            )
            db.commit()

            flash('Your listing has been updated!', 'success')
            return redirect(url_for('product.product_view', product_id=product_id))

        return render_template('product/edit.html', title='Edit Listing', form=form, product=product)

    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on product edit: {e}")
        flash('An error occurred while updating your listing.', 'danger')
        return redirect(url_for('product.product_view', product_id=product_id))

@bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete(product_id):
    db = get_db()

    try:
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()

        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))

        if product['seller_id'] != current_user.id:
            flash('You do not have permission to delete this listing.', 'danger')
            return redirect(url_for('product.product_view', product_id=product_id))

        if product['image_path']:
            image_path = os.path.join(current_app.root_path, 'static', product['image_path'])
            if os.path.exists(image_path):
                os.remove(image_path)

        db.execute('DELETE FROM products WHERE id = ?', (product_id,))
        db.commit()

        flash('Your listing has been deleted.', 'success')
        return redirect(url_for('main.index'))

    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on product deletion: {e}")
        flash('An error occurred while deleting your listing.', 'danger')
        return redirect(url_for('product.product_view', product_id=product_id))

@bp.route('/category/<int:category_id>')
def by_category(category_id):
    db = get_db()
    try:
        category = db.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()

        if not category:
            flash('Category not found.', 'warning')
            return redirect(url_for('main.index'))

        products = db.execute(
            'SELECT p.*, u.name as seller_name '
            'FROM products p '
            'JOIN users u ON p.seller_id = u.id '
            'WHERE p.category_id = ? AND p.is_sold = 0 '
            'ORDER BY p.date_posted DESC',
            (category_id,)
        ).fetchall()

        return render_template(
            'product/category.html',
            title=f"{category['name']} Listings",
            category=category,
            products=products
        )

    except sqlite3.Error as e:
        print(f"DB Error on category view: {e}")
        flash('An error occurred while retrieving category listings.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/search')
def search():
    query = request.args.get('q', '')

    if not query:
        return redirect(url_for('main.index'))

    db = get_db()
    try:
        search_term = f"%{query}%"
        products = db.execute(
            'SELECT p.*, u.name as seller_name, c.name as category_name '
            'FROM products p '
            'JOIN users u ON p.seller_id = u.id '
            'JOIN categories c ON p.category_id = c.id '
            'WHERE (p.title LIKE ? OR p.description LIKE ?) AND p.is_sold = 0 '
            'ORDER BY p.date_posted DESC',
            (search_term, search_term)
        ).fetchall()

        return render_template(
            'product/search.html',
            title=f'Search Results for "{query}"',
            query=query,
            products=products
        )

    except sqlite3.Error as e:
        print(f"DB Error on search: {e}")
        flash('An error occurred while searching for products.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/toggle-sold/<int:product_id>', methods=['POST'])
@login_required
def toggle_sold(product_id):
    db = get_db()

    try:
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()

        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))

        if product['seller_id'] != current_user.id:
            flash('You do not have permission to update this listing.', 'danger')
            return redirect(url_for('product.product_view', product_id=product_id))

        new_status = 1 if product['is_sold'] == 0 else 0
        db.execute('UPDATE products SET is_sold = ? WHERE id = ?', (new_status, product_id))
        db.commit()

        status_msg = 'marked as sold' if new_status == 1 else 'marked as available'
        flash(f'Your listing has been {status_msg}.', 'success')
        return redirect(url_for('product.product_view', product_id=product_id))

    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on toggle sold status: {e}")
        flash('An error occurred while updating your listing status.', 'danger')
        return redirect(url_for('product.product_view', product_id=product_id))

@bp.route('/like/<int:product_id>', methods=['POST'])
@login_required
def like(product_id):
    db = get_db()
    user_id = current_user.id
    print(f"User ID: {user_id}, Product ID: {product_id}")

    try:
        existing_like = db.execute(
            'SELECT 1 FROM likes WHERE user_id = ? AND product_id = ? LIMIT 1',
            (user_id, product_id)
        ).fetchone()

        if existing_like:
            db.execute(
                'DELETE FROM likes WHERE user_id = ? AND product_id = ?',
                (user_id, product_id)
            )
            db.commit()
            print(f"Unliked product {product_id} by user {user_id}")
        else:
            db.execute(
                'INSERT INTO likes (user_id, product_id, timestamp) VALUES (?, ?, ?)',
                (user_id, product_id, datetime.now())
            )
            db.commit()
            print(f"Liked product {product_id} by user {user_id}")

    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on toggling like for product {product_id} by user {user_id}: {e}")
        flash('An error occurred. Please try again.', 'danger')

    return redirect(url_for('product.product_view', product_id=product_id))

@bp.route('/comment/<int:product_id>', methods=['POST'])
@login_required
def comment(product_id):
    db = get_db()
    text = request.form.get('text')
    user_id = current_user.id

    if not text or not text.strip():
        flash('Comment cannot be empty.', 'warning')
        return redirect(url_for('product.product_view', product_id=product_id, _anchor='comments'))

    try:
        db.execute(
            'INSERT INTO comments (user_id, product_id, text, timestamp) VALUES (?, ?, ?, ?)',
            (user_id, product_id, text.strip(), datetime.now())
        )
        db.commit()
        flash('Your comment has been posted!', 'success')

    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on commenting for product {product_id} by user {user_id}: {e}")
        flash('An error occurred while posting your comment.', 'danger')

    return redirect(url_for('product.product_view', product_id=product_id, _anchor='comments'))