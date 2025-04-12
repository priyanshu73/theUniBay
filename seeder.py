# seed.py
# Location: Place this file in the project root directory (THEUNIBAY/)
# Usage:
# 1. Activate your virtual environment: venv/Scripts/activate (or source venv/bin/activate)
# 2. Ensure dependencies are installed: pip install Faker Werkzeug
# 3. Initialize the database schema first: flask init-db (or however your init command is set up)
# 4. Run this script from the project root: python seed.py
# Note: This script creates DATABASE entries with placeholder image paths.
#       For images to display, you need actual image files placed in
#       'app/static/product_images/' matching the placeholder names,
#       or rely on users uploading images via the application.

import sqlite3
import os
import random
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
import uuid # Using uuid for random filenames like in save_image

# --- Configuration ---
# Assume this script is in the project root directory (THEUNIBAY/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Correct path based on the image: instance folder in the root, db file named default.sqlite
DB_PATH = os.path.join(BASE_DIR, 'instance', 'default.sqlite')

NUM_USERS = 15
NUM_PRODUCTS_PER_USER_RANGE = (1, 5) # Each user lists between 1 and 5 products
# NUM_IMAGES_PER_PRODUCT_RANGE = (0, 3) # REMOVED - Not using product_images table based on product.py
NUM_COMMENTS_PER_PRODUCT_RANGE = (0, 5)
NUM_REVIEWS_PER_USER_RANGE = (0, 4) # Number of reviews *received* by a user
LIKE_PROBABILITY = 0.3 # Chance any given user likes any given product

# --- Initialize Faker ---
fake = Faker()

# --- Helper Functions ---
def get_db_connection():
    """Establishes a connection to the database."""
    if not os.path.exists(os.path.dirname(DB_PATH)):
         print(f"Warning: Directory {os.path.dirname(DB_PATH)} does not exist. Creating it.")
         os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        print("Please ensure you have initialized the database first (e.g., using 'flask init-db').")
        exit()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Optional: access columns by name
        conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign keys
        print(f"Database connection successful to {DB_PATH}.")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        exit()

def get_existing_ids(conn, table_name):
    """Fetches all IDs from a given table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id FROM {table_name}")
        return [row['id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching IDs from {table_name}: {e}")
        return []

# --- Seeding Functions ---

def seed_campuses(conn):
    """Seeds the campuses table."""
    print("Seeding campuses...")
    campuses_data = [
        ('Main Campus', fake.city(), fake.state_abbr()),
        ('North Campus', fake.city(), fake.state_abbr()),
        ('West Campus', fake.city(), fake.state_abbr()),
        ('Online Division', 'Virtual', 'NA'),
    ]
    try:
        cursor = conn.cursor()
        # Use INSERT OR IGNORE to avoid errors if campuses already exist
        cursor.executemany("INSERT OR IGNORE INTO campuses (name, city, state) VALUES (?, ?, ?)", campuses_data)
        conn.commit()
        print(f"Campuses seeded/updated.")
        return get_existing_ids(conn, 'campuses')
    except sqlite3.Error as e:
        print(f"Error seeding campuses: {e}")
        conn.rollback()
        return []

def seed_categories(conn):
    """Ensures categories are present and gets their IDs."""
    print("Verifying/Seeding categories...")
    # Categories might already be present from schema.sql's INSERT OR IGNORE.
    # Running it here ensures they exist if schema didn't have it or if run independently.
    categories_data = [
        ('Textbooks', 'Course textbooks and study materials'),
        ('Electronics', 'Computers, phones, calculators and other electronic devices'),
        ('Furniture', 'Dorm and apartment furniture'),
        ('Clothing', 'Apparel, shoes, and accessories'),
        ('School Supplies', 'Notebooks, pens, backpacks and other supplies'),
        ('Sports Equipment', 'Athletic gear and equipment'),
        ('Musical Instruments', 'Instruments and accessories'),
        ('Event Tickets', 'Tickets to campus and local events'),
        ('Services', 'Tutoring, repairs, and other services'),
        ('Other', 'Miscellaneous items')
    ]
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", categories_data)
        conn.commit()
        print("Categories verified/seeded.")
        return get_existing_ids(conn, 'categories')
    except sqlite3.Error as e:
        print(f"Error verifying/seeding categories: {e}")
        conn.rollback()
        return []

def seed_users(conn, num_users, campus_ids):
    """Seeds the users table."""
    print(f"Seeding {num_users} users...")
    users_data = []
    for i in range(num_users):
        name = fake.name()
        # Create predictable emails for first few users for easier testing/login
        if i == 0:
            email = 'user1@test.edu'
        elif i == 1:
             email = 'user2@test.edu'
        else:
            email = fake.unique.email()
            # Basic attempt at .edu - replace with more robust logic if needed
            if '@' in email and not email.endswith(('.edu', '.org', '.com')): # Allow common domains too
                 base_email = email.split('@')[0]
                 email = f"{base_email}@fake-uni.edu" # Use a fake edu domain

        password = 'password' # Use a common password for seeded data
        hashed_password = generate_password_hash(password)
        join_date = fake.date_time_between(start_date='-2y', end_date='now')
        profile_info = fake.paragraph(nb_sentences=3)
        # Assign a random campus ID if campuses exist
        assigned_campus_id = random.choice(campus_ids) if campus_ids else None
        users_data.append((name, email, hashed_password, join_date, profile_info, assigned_campus_id))

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, join_date, profile_info, campus_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()
        print(f"Seeded {num_users} users. Default password for all is 'password'. Test emails: user1@test.edu, user2@test.edu")
        return get_existing_ids(conn, 'users')
    except sqlite3.Error as e:
        # Handle unique constraint error gracefully if emails collide (rare with unique)
        if "UNIQUE constraint failed: users.email" in str(e):
             print(f"Warning: Skipped duplicate email during seeding: {e}")
             # Still try to fetch IDs that were inserted before the error
             conn.rollback() # Rollback the failed insert
             return get_existing_ids(conn, 'users')
        else:
            print(f"Error seeding users: {e}")
            conn.rollback()
            return []


def seed_products(conn, user_ids, category_ids, num_products_range):
    """Seeds the products table based on the project schema and product.py."""
    print("Seeding products...")
    if not user_ids or not category_ids:
        print("Cannot seed products without users and categories.")
        return []

    products_data = []
    product_id_map = {} # Store seller_id for reviews later: {product_id: seller_id}

    for seller_id in user_ids:
        num_products = random.randint(num_products_range[0], num_products_range[1])
        for _ in range(num_products):
            title = fake.bs().title() # Generate more product-like titles
            description = fake.paragraph(nb_sentences=5)
            price = round(random.uniform(5.0, 500.0), 2)
            condition = random.choice(['New', 'Used - Like New', 'Used - Good', 'Used - Fair', 'Used - Poor'])

            # **MODIFIED**: Generate placeholder image path consistent with save_image() format
            # We are just creating path strings, not actual files.
            # Use a simple placeholder name structure for predictability in seeding context.
            placeholder_filename = f"placeholder_{uuid.uuid4().hex[:8]}.jpg" # Example: placeholder_a1b2c3d4.jpg
            image_path = f"product_images/{placeholder_filename}" # Relative path like in save_image

            date_posted = fake.date_time_between(start_date='-1y', end_date='now')
            category_id = random.choice(category_ids)
            is_sold = fake.boolean(chance_of_getting_true=15) # 15% chance sold

            # Match the columns in the second schema provided
            products_data.append((
                title, description, price, condition, image_path,
                date_posted, category_id, seller_id, is_sold
            ))

    try:
        cursor = conn.cursor()
        inserted_product_ids = []
        for product in products_data:
            # Match the columns in the second schema provided
            cursor.execute("""
                INSERT INTO products (title, description, price, condition, image_path,
                                      date_posted, category_id, seller_id, is_sold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product)
            last_id = cursor.lastrowid
            inserted_product_ids.append(last_id)
            product_id_map[last_id] = product[7] # Store product_id -> seller_id mapping (seller_id is 8th element, index 7)

        conn.commit()
        print(f"Seeded {len(inserted_product_ids)} products.")
        return product_id_map # Return the map instead of just IDs
    except sqlite3.Error as e:
        print(f"Error seeding products: {e}")
        conn.rollback()
        return {}

# REMOVED seed_product_images function as product.py doesn't use the product_images table

def seed_comments(conn, user_ids, product_ids, num_comments_range):
    """Seeds the comments table."""
    if not user_ids or not product_ids:
        print("Cannot seed comments without users and products.")
        return
    print("Seeding comments...")
    comments_data = []
    # Select a subset of products to receive comments
    products_to_comment = random.sample(product_ids, k=min(len(product_ids), int(len(user_ids) * 1.5)))

    for product_id in products_to_comment:
        num_comments = random.randint(num_comments_range[0], num_comments_range[1])
        possible_commenters = list(user_ids) # Can comment on own product in this seed
        if not possible_commenters: continue

        for _ in range(num_comments):
             user_id = random.choice(possible_commenters)
             text = fake.sentence(nb_words=random.randint(5, 25))
             timestamp = fake.date_time_between(start_date='-6m', end_date='now')
             comments_data.append((user_id, product_id, text, timestamp))

    if not comments_data:
        print("No comments generated.")
        return

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO comments (user_id, product_id, text, "timestamp")
            VALUES (?, ?, ?, ?)
        """, comments_data)
        conn.commit()
        print(f"Seeded {len(comments_data)} comments.")
    except sqlite3.Error as e:
        print(f"Error seeding comments: {e}")
        conn.rollback()

def seed_reviews(conn, user_ids, product_id_map, num_reviews_range):
    """Seeds the reviews table."""
    if not user_ids or len(user_ids) < 2 or not product_id_map:
        print("Cannot seed reviews without at least 2 users and products.")
        return
    print("Seeding reviews...")
    reviews_data = []

    # Determine potential sellers (users who have listed products)
    sellers = list(set(product_id_map.values()))
    potential_reviewers = list(user_ids)

    for reviewed_user_id in sellers:
        num_reviews = random.randint(num_reviews_range[0], num_reviews_range[1])
        # Filter out the reviewed user from potential reviewers
        possible_reviewers = [r for r in potential_reviewers if r != reviewed_user_id]
        if not possible_reviewers: continue

        # Find products sold by this user to potentially link reviews
        products_by_seller = [pid for pid, sid in product_id_map.items() if sid == reviewed_user_id]

        # Limit number of reviews per seller based on available unique reviewers
        num_reviews = min(num_reviews, len(possible_reviewers))

        reviewers_for_this_seller = random.sample(possible_reviewers, k=num_reviews)

        for reviewer_id in reviewers_for_this_seller:

            # Optionally link to a product sold by the reviewed user
            product_id = random.choice(products_by_seller) if products_by_seller and random.random() < 0.7 else None # 70% chance to link

            rating = random.randint(1, 5)
            comment = fake.paragraph(nb_sentences=2) if random.random() < 0.8 else None # 80% chance of comment text
            timestamp = fake.date_time_between(start_date='-6m', end_date='now')

            # Ensure reviewer is not the same as reviewed user (already handled by filtering)
            if reviewer_id != reviewed_user_id:
                reviews_data.append((reviewer_id, reviewed_user_id, product_id, rating, comment, timestamp))

    if not reviews_data:
        print("No reviews generated.")
        return

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO reviews (reviewer_id, reviewed_user_id, product_id, rating, comment, "timestamp")
            VALUES (?, ?, ?, ?, ?, ?)
        """, reviews_data)
        conn.commit()
        print(f"Seeded {len(reviews_data)} reviews.")
    except sqlite3.Error as e:
        # Ignore unique constraint errors if the same review is attempted twice (unlikely with current logic)
        if "UNIQUE constraint failed" in str(e):
             print(f"Skipped duplicate review: {e}")
             conn.rollback() # Needs rollback even if ignoring
        else:
             print(f"Error seeding reviews: {e}")
             conn.rollback()


def seed_likes(conn, user_ids, product_ids, like_probability):
    """Seeds the likes table."""
    if not user_ids or not product_ids:
        print("Cannot seed likes without users and products.")
        return
    print("Seeding likes...")
    likes_data = []
    for user_id in user_ids:
        # Each user likes a random subset of products
        num_likes = int(len(product_ids) * like_probability * (random.random() + 0.5)) # Vary probability slightly
        products_liked_by_user = random.sample(product_ids, k=min(num_likes, len(product_ids)))
        for product_id in products_liked_by_user:
                timestamp = fake.date_time_between(start_date='-6m', end_date='now')
                likes_data.append((user_id, product_id, timestamp))

    if not likes_data:
        print("No likes generated.")
        return

    try:
        cursor = conn.cursor()
        # Use INSERT OR IGNORE because the primary key (user_id, product_id) prevents duplicates
        cursor.executemany("""
            INSERT OR IGNORE INTO likes (user_id, product_id, "timestamp")
            VALUES (?, ?, ?)
        """, likes_data)
        conn.commit()
        # Get actual count of inserted rows after ignoring duplicates
        # This is an approximation as total_changes is cumulative
        changes = conn.total_changes
        print(f"Seeded likes (duplicates ignored). Approx {len(likes_data)} like attempts made.")
    except sqlite3.Error as e:
        print(f"Error seeding likes: {e}")
        conn.rollback()

# --- Main Execution ---
if __name__ == "__main__":
    conn = get_db_connection()
    if not conn:
        exit()

    start_time = datetime.now()
    print(f"\n--- Starting Database Seeding ({start_time.strftime('%Y-%m-%d %H:%M:%S')}) ---")

    try:
        # Seed in order of dependency
        campus_ids = seed_campuses(conn)
        category_ids = seed_categories(conn) # Get IDs after ensuring they exist
        user_ids = seed_users(conn, NUM_USERS, campus_ids)

        # Seed products and get a map of {product_id: seller_id}
        product_id_map = seed_products(conn, user_ids, category_ids, NUM_PRODUCTS_PER_USER_RANGE)
        product_ids = list(product_id_map.keys()) # Get list of product IDs

        if product_ids:
             # REMOVED call to seed_product_images as it's not used in product.py
             seed_comments(conn, user_ids, product_ids, NUM_COMMENTS_PER_PRODUCT_RANGE)
             seed_likes(conn, user_ids, product_ids, LIKE_PROBABILITY)

        # Seed reviews using the product_id_map to know who sold what
        seed_reviews(conn, user_ids, product_id_map, NUM_REVIEWS_PER_USER_RANGE)

        end_time = datetime.now()
        print(f"\n--- Database seeding completed successfully ({end_time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
        print(f"--- Total time: {end_time - start_time} ---")

    except Exception as e:
        print(f"\n--- An error occurred during seeding: {e} ---")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        conn.rollback() # Roll back any partial changes on general error
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")