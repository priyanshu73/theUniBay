# app/product.py - FIXED
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

# Create Blueprint
bp = Blueprint('product', __name__, url_prefix='/product')

# Helper function to save uploaded image
def save_image(form_image):
    if not form_image.data:
        return None
    
    # Create a secure filename and save the file
    random_hex = os.urandom(8).hex()
    _, file_ext = os.path.splitext(form_image.data.filename)
    filename = random_hex + file_ext
    
    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, 'static', 'product_images')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    file_path = os.path.join(upload_dir, filename)
    form_image.data.save(file_path)
    
    # Return the relative path for database storage
    return f'product_images/{filename}'

# --- Create Product Route ---
@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ProductForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        # Convert price to float for SQLite compatibility
        price = float(form.price.data)
        category_id = form.category.data
        condition = form.condition.data
        
        # Handle image upload if provided
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
            return redirect(url_for('product.view', product_id=product_id))
            
        except sqlite3.Error as e:
            db.rollback()
            flash(f'An error occurred while creating your listing: {e}', 'danger')
            print(f"DB Error on product creation: {e}")  # Log the error
    
    # If GET request or form validation failed
    return render_template('product/create.html', title='Create Listing', form=form)

# --- View Product Route ---
@bp.route('/<int:product_id>')
def view(product_id):
    db = get_db()
    try:
        # Join with users and categories to get seller and category info
        product = db.execute(
            'SELECT p.*, u.name as seller_name, u.email as seller_email, c.name as category_name '
            'FROM products p '
            'JOIN users u ON p.seller_id = u.id '
            'JOIN categories c ON p.category_id = c.id '
            'WHERE p.id = ?',
            (product_id,)
        ).fetchone()
        
        if product:
            return render_template('product/view.html', title=product['title'], product=product)
        else:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))
            
    except sqlite3.Error as e:
        print(f"DB Error on product view: {e}")  # Log the error
        flash('An error occurred while retrieving the product.', 'danger')
        return redirect(url_for('main.index'))

# --- Edit Product Route ---
@bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    db = get_db()
    
    # First, check if the product exists and belongs to the current user
    try:
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()
        
        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))
            
        if product['seller_id'] != current_user.id:
            flash('You do not have permission to edit this listing.', 'danger')
            return redirect(url_for('product.view', product_id=product_id))
            
        # If we got here, the product exists and belongs to the current user
        form = ProductForm()
        
        if request.method == 'GET':
            # Pre-populate the form with existing data
            form.title.data = product['title']
            form.description.data = product['description']
            form.price.data = product['price']
            form.category.data = product['category_id']
            form.condition.data = product['condition']
            
        if form.validate_on_submit():
            # Process the form submission
            title = form.title.data
            description = form.description.data
            # Convert price to float for SQLite compatibility
            price = float(form.price.data)
            category_id = form.category.data
            condition = form.condition.data
            
            # Handle image upload if provided
            if form.image.data:
                # Delete old image if it exists
                if product['image_path']:
                    old_image_path = os.path.join(current_app.root_path, 'static', product['image_path'])
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                image_path = save_image(form.image)
            else:
                # Keep existing image
                image_path = product['image_path']
                
            # Update the product in the database
            db.execute(
                'UPDATE products SET title = ?, description = ?, price = ?, '
                'category_id = ?, condition = ?, image_path = ? WHERE id = ?',
                (title, description, price, category_id, condition, image_path, product_id)
            )
            db.commit()
            
            flash('Your listing has been updated!', 'success')
            return redirect(url_for('product.view', product_id=product_id))
            
        return render_template('product/edit.html', title='Edit Listing', form=form, product=product)
        
    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on product edit: {e}")  # Log the error
        flash('An error occurred while updating your listing.', 'danger')
        return redirect(url_for('product.view', product_id=product_id))

# --- Delete Product Route ---
@bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete(product_id):
    db = get_db()
    
    try:
        # Check if product exists and belongs to current user
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()
        
        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))
            
        if product['seller_id'] != current_user.id:
            flash('You do not have permission to delete this listing.', 'danger')
            return redirect(url_for('product.view', product_id=product_id))
            
        # Delete the image file if it exists
        if product['image_path']:
            image_path = os.path.join(current_app.root_path, 'static', product['image_path'])
            if os.path.exists(image_path):
                os.remove(image_path)
                
        # Delete the product from the database
        db.execute('DELETE FROM products WHERE id = ?', (product_id,))
        db.commit()
        
        flash('Your listing has been deleted.', 'success')
        return redirect(url_for('main.index'))
        
    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on product deletion: {e}")  # Log the error
        flash('An error occurred while deleting your listing.', 'danger')
        return redirect(url_for('product.view', product_id=product_id))

# --- List Products by Category ---
@bp.route('/category/<int:category_id>')
def by_category(category_id):
    db = get_db()
    try:
        # Get category info
        category = db.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
        
        if not category:
            flash('Category not found.', 'warning')
            return redirect(url_for('main.index'))
            
        # Get products in this category
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
        print(f"DB Error on category view: {e}")  # Log the error
        flash('An error occurred while retrieving category listings.', 'danger')
        return redirect(url_for('main.index'))

# --- Search Products ---
@bp.route('/search')
def search():
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('main.index'))
        
    db = get_db()
    try:
        # Search for products matching query in title or description
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
        print(f"DB Error on search: {e}")  # Log the error
        flash('An error occurred while searching for products.', 'danger')
        return redirect(url_for('main.index'))

# --- Mark Product as Sold/Unsold ---
@bp.route('/toggle-sold/<int:product_id>', methods=['POST'])
@login_required
def toggle_sold(product_id):
    db = get_db()
    
    try:
        # Check if product exists and belongs to current user
        product = db.execute(
            'SELECT * FROM products WHERE id = ?', (product_id,)
        ).fetchone()
        
        if not product:
            flash('Product not found.', 'warning')
            return redirect(url_for('main.index'))
            
        if product['seller_id'] != current_user.id:
            flash('You do not have permission to update this listing.', 'danger')
            return redirect(url_for('product.view', product_id=product_id))
            
        # Toggle the is_sold status
        new_status = 1 if product['is_sold'] == 0 else 0
        db.execute('UPDATE products SET is_sold = ? WHERE id = ?', (new_status, product_id))
        db.commit()
        
        status_msg = 'marked as sold' if new_status == 1 else 'marked as available'
        flash(f'Your listing has been {status_msg}.', 'success')
        return redirect(url_for('product.view', product_id=product_id))
        
    except sqlite3.Error as e:
        db.rollback()
        print(f"DB Error on toggle sold status: {e}")  # Log the error
        flash('An error occurred while updating your listing status.', 'danger')
        return redirect(url_for('product.view', product_id=product_id))