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
import re # Import regular expressions for domain generation
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
import uuid

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'default.sqlite')

NUM_USERS = 25
NUM_PRODUCTS_PER_USER_RANGE = (2, 7) # Slightly increased range
NUM_COMMENTS_PER_PRODUCT_RANGE = (0, 6)
NUM_REVIEWS_PER_USER_RANGE = (0, 5)
LIKE_PROBABILITY = 0.35

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
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
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

# **NEW Helper Function: Generate Domain from Campus Name**
def generate_domain(campus_name):
    """Generates a plausible .edu domain from a campus name."""
    name = campus_name.lower()
    # Remove common prefixes/suffixes and articles
    name = re.sub(r'(university of|the|institute of technology|state university|university$| at | institute$)', '', name).strip()
    # Handle specific known cases or abbreviations if needed
    if 'harvard' in name: return 'harvard.edu'
    if 'stanford' in name: return 'stanford.edu'
    if 'texas' in name and 'austin' in name: return 'utexas.edu' # UT Austin specific
    if 'mit' in name or 'massachusetts' in name: return 'mit.edu'
    if 'new york' in name or 'nyu' in name: return 'nyu.edu'
    if 'southern california' in name or 'usc' in name: return 'usc.edu'
    if 'michigan' in name and 'ann arbor' in name: return 'umich.edu' # UMich specific
    if 'arizona state' in name or 'asu' in name: return 'asu.edu'
    if 'colorado' in name and 'boulder' in name: return 'colorado.edu' # CU Boulder specific

    # General approach: remove spaces, take first part if long, add .edu
    parts = re.split(r'[ ,-]+', name)
    if len(parts) > 1 and len(parts[0]) > 3:
        domain_base = parts[0]
    else:
        domain_base = "".join(parts)

    # Limit length slightly
    domain_base = domain_base[:15]

    return f"{domain_base}.edu"


# --- Seeding Functions ---

def seed_campuses(conn):
    """Seeds the campuses table and returns an ID-to-Name map."""
    print("Seeding campuses...")
    campuses_data = [
        ('Harvard University', 'Cambridge', 'MA'),
        ('Stanford University', 'Stanford', 'CA'),
        ('University of Texas at Austin', 'Austin', 'TX'),
        ('University of Washington', 'Seattle', 'WA'),
        ('New York University', 'New York', 'NY'),
        ('University of Florida', 'Gainesville', 'FL'),
        ('Ohio State University', 'Columbus', 'OH'),
        ('University of Michigan', 'Ann Arbor', 'MI'),
        ('Georgia Institute of Technology', 'Atlanta', 'GA'),
        ('University of Southern California', 'Los Angeles', 'CA'),
        ('Arizona State University', 'Tempe', 'AZ'),
        ('University of Colorado Boulder', 'Boulder', 'CO')
    ]
    campus_map = {}
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT OR IGNORE INTO campuses (name, city, state) VALUES (?, ?, ?)", campuses_data)
        conn.commit()
        print(f"Campuses seeded/updated. ({len(campuses_data)} records)")
        # Fetch the inserted/existing campuses to build the map
        cursor.execute("SELECT id, name FROM campuses")
        campus_map = {row['id']: row['name'] for row in cursor.fetchall()}
        return campus_map # **RETURN MAP {id: name}**
    except sqlite3.Error as e:
        print(f"Error seeding campuses: {e}")
        conn.rollback()
        return {}

def seed_categories(conn):
    """Ensures categories are present and returns an ID-to-Name map."""
    print("Verifying/Seeding categories...")
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
    category_map = {}
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", categories_data)
        conn.commit()
        print("Categories verified/seeded.")
        cursor.execute("SELECT id, name FROM categories")
        category_map = {row['id']: row['name'] for row in cursor.fetchall()}
        return category_map
    except sqlite3.Error as e:
        print(f"Error verifying/seeding categories: {e}")
        conn.rollback()
        return {}

def seed_users(conn, num_users, campus_map): # Takes campus_map now
    """Seeds users with campus-specific .edu emails."""
    print(f"Seeding {num_users} users...")
    if not campus_map:
        print("Warning: Cannot generate campus-specific emails without campus data.")
        return []

    campus_ids = list(campus_map.keys())
    users_data = []
    generated_emails = set() # Track emails to ensure uniqueness if Faker misses

    for i in range(num_users):
        name = fake.name()
        password = 'password'
        hashed_password = generate_password_hash(password)
        join_date = fake.date_time_between(start_date='-2y', end_date='now')
        major = fake.random_element(elements=('Computer Science', 'Business Admin', 'Psychology', 'Engineering', 'Biology', 'Communications', 'Art History', 'Economics', 'Nursing'))
        year = fake.random_element(elements=('Freshman', 'Sophomore', 'Junior', 'Senior', 'Grad Student'))
        profile_info = f"{year} studying {major}. Looking to buy/sell {fake.random_element(elements=('textbooks', 'dorm stuff', 'electronics', 'clothing'))}. {fake.sentence(nb_words=random.randint(4, 8))}"

        assigned_campus_id = random.choice(campus_ids)
        campus_name = campus_map.get(assigned_campus_id, "Unknown Campus")

        # **UPDATED: Generate campus-specific .edu email**
        domain = generate_domain(campus_name)
        username_base = fake.user_name()
        email = f"{username_base}@{domain}"

        # Override for first two users for easy testing, using their assigned campus domain
        if i == 0:
            username_base = 'user1'
            email = f"{username_base}@{domain}"
        elif i == 1:
            username_base = 'user2'
            email = f"{username_base}@{domain}"

        # Ensure uniqueness (simple retry mechanism)
        retry_count = 0
        while email in generated_emails and retry_count < 5:
            username_base = fake.user_name() + str(random.randint(1,99))
            email = f"{username_base}@{domain}"
            retry_count += 1
        if email in generated_emails: # Still duplicate after retries? Skip user.
             print(f"Warning: Could not generate unique email for domain {domain}. Skipping user.")
             continue

        generated_emails.add(email)
        users_data.append((name, email, hashed_password, join_date, profile_info, assigned_campus_id))

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, join_date, profile_info, campus_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()
        print(f"Seeded {len(users_data)} users. Default password: 'password'. Check DB for test user emails.")
        return get_existing_ids(conn, 'users')
    except sqlite3.Error as e:
        # This uniqueness check might be redundant now but kept as safety
        if "UNIQUE constraint failed: users.email" in str(e):
             print(f"Warning: Skipped duplicate email during seeding (DB constraint): {e}")
             conn.rollback()
             return get_existing_ids(conn, 'users')
        else:
            print(f"Error seeding users: {e}")
            conn.rollback()
            return []


def seed_products(conn, user_ids, category_map, num_products_range):
    """Seeds products with CATEGORY-SPECIFIC placeholder images."""
    print("Seeding products...")
    if not user_ids or not category_map:
        print("Cannot seed products without users and categories.")
        return []

    category_ids = list(category_map.keys())
    products_data = []
    product_id_map = {}

    # --- Define mapping from category name to placeholder filename ---
    # NOTE: Ensure these filenames EXACTLY match the files you saved in app/static/product_images/
    category_image_map = {
        'Textbooks': 'textbooks.jpg',
        'Electronics': 'electronics.jpg',
        'Furniture': 'furniture.jpg',
        'Clothing': 'clothing.jpg',
        'School Supplies': 'school_supplies.jpg',
        'Sports Equipment': 'sports_equipment.jpg',
        'Musical Instruments': 'musical_instruments.jpg',
        'Event Tickets': 'event_tickets.jpg',
        'Services': 'services.jpg',
        'Other': 'other.jpg' # Default/fallback
    }

    for seller_id in user_ids:
        num_products = random.randint(num_products_range[0], num_products_range[1])
        for _ in range(num_products):
            category_id = random.choice(category_ids)
            category_name = category_map.get(category_id, 'Other')

            price = round(random.uniform(5.0, 500.0), 2)
            condition = random.choice(['New', 'Used - Like New', 'Used - Good', 'Used - Fair', 'Used - Poor'])
            date_posted = fake.date_time_between(start_date='-1y', end_date='now')
            is_sold = fake.boolean(chance_of_getting_true=15)

            # **MODIFIED: Select image based on category name**
            placeholder_filename = category_image_map.get(category_name, 'other.jpg') # Use map, default to other.jpg
            image_path = f"product_images/{placeholder_filename}" # Construct path

            # **Product Title/Description Generation (Keep the relevant logic from previous version)**
            title = f"{condition} {category_name} Item" # Initial default
            description = f"Selling a {category_name.lower()}. Condition: {condition}." # Initial default

            # (Keep all the specific if/elif blocks for title/description/price adjustments)
            if category_name == 'Textbooks':
                course = fake.random_element(elements=('CS 101', 'MATH 210', 'BIO 150', 'ENG 102', 'HIST 205', 'CHEM 111', 'PSYC 100'))
                adj = fake.random_element(elements=('Gently Used', 'Like New', 'Acceptable Condition', 'Required'))
                title = f"{adj} {course} Textbook ({random.randint(3, 9)}th Ed.)"
                desc_detail = fake.random_element(elements=('Some highlighting.', 'No writing inside.', 'Minimal wear on cover.', 'Access code likely used.', 'Needed for Prof. Smith\'s class.'))
                description = f"Textbook for {course}. {desc_detail} Condition: {condition}. ISBN: {fake.isbn13()}."
                price = round(random.uniform(15.0, 150.0), 2)
            elif category_name == 'Electronics':
                item = fake.random_element(elements=('Laptop', 'Monitor', 'Headphones', 'Keyboard', 'Mouse', 'Calculator', 'Webcam', 'Tablet', 'Charger', 'Speaker'))
                brand = fake.random_element(elements=('Dell', 'HP', 'Logitech', 'Sony', 'Apple', 'Samsung', 'TI', 'Anker', 'Microsoft', 'Bose'))
                title = f"{condition} {brand} {item}"
                desc_detail = fake.random_element(elements=('Works perfectly.', 'Used for about a year.', 'Minor cosmetic scratches.', 'Includes original charger/cable.', 'Selling because I upgraded.'))
                description = f"Selling my {brand} {item}. {desc_detail} Condition: {condition}. Model: {fake.word().upper()}-{random.randint(100, 999)}."
                price = round(random.uniform(10.0, 600.0), 2)
            # ... include ALL other elif blocks for other categories here ...
            elif category_name == 'Furniture': # Example start
                item = fake.random_element(elements=('Desk Lamp', 'Mini Fridge', 'Bookshelf', 'Desk Chair', 'Futon Couch', 'Bedside Table', 'Floor Lamp', 'Storage Ottoman', 'Mirror'))
                adj = fake.random_element(elements=('Compact', 'Sturdy', 'IKEA', 'Used', 'Foldable', 'Adjustable'))
                title = f"{adj} {item} - {condition}"
                desc_detail = fake.random_element(elements=('Perfect for dorm rooms.', 'Used for one semester.', 'Need gone ASAP - moving out.', 'Great for small spaces.', 'Smoke-free home.'))
                description = f"{item} for sale. {desc_detail} Condition: {condition}. Approx Dimensions: {random.randint(10, 40)}x{random.randint(10, 30)} inches."
                price = round(random.uniform(10.0, 200.0), 2)
            # ... (CONTINUE FOR: Clothing, School Supplies, Sports Equipment, etc.) ...
            elif category_name == 'Other':
                 item = fake.random_element(elements=('Wall Tapestry', 'Video Game', 'Board Game', 'Plant', 'Art Print', 'Kitchenware Set', 'Bike Lock'))
                 adj = fake.random_element(elements=('Cool', 'Fun', 'Unused', 'Quirky', 'Handmade', 'Durable'))
                 title = f"{adj} {item} - {condition}"
                 desc_detail = fake.random_element(elements=('Random item for sale.', 'Clearing out my room.', 'Maybe someone needs this?', 'Make an offer!'))
                 description = f"Selling: {item}. {desc_detail} Condition: {condition}."
                 price = round(random.uniform(1.0, 50.0), 2)

            # N/A conditions don't need special title handling here if done above
            if category_name in ['Event Tickets', 'Services']:
                 condition = 'N/A'


            products_data.append((
                title, description, price, condition, image_path, # Use the category-specific image_path
                date_posted, category_id, seller_id, is_sold
            ))

    # Database insertion logic (remains the same)
    try:
        cursor = conn.cursor()
        inserted_product_ids = []
        for product in products_data:
            cursor.execute("""
                INSERT INTO products (title, description, price, condition, image_path,
                                      date_posted, category_id, seller_id, is_sold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product)
            last_id = cursor.lastrowid
            inserted_product_ids.append(last_id)
            product_id_map[last_id] = product[7] # product[7] is seller_id

        conn.commit()
        print(f"Seeded {len(inserted_product_ids)} products.")
        return product_id_map
    except sqlite3.Error as e:
        print(f"Error seeding products: {e}")
        conn.rollback()
        return {}

# ... (Keep seed_comments, seed_reviews, seed_likes, and __main__ block) ...

# --- Add note to __main__ block or top comments ---
# Make sure to remind the user to place the category images
if __name__ == "__main__":
     print("\n--- IMPORTANT ---")
     print("Ensure category placeholder images (textbooks.jpg, electronics.jpg, etc.)")
     print("are placed in the 'app/static/product_images/' directory.")
     print("-----------------\n")


# (seed_comments, seed_reviews, seed_likes remain the same as the previous 'relevant text' version)
# ... copy seed_comments, seed_reviews, seed_likes functions from the previous good version ...
def seed_comments(conn, user_ids, product_ids, num_comments_range):
    """Seeds comments with more relevant text."""
    if not user_ids or not product_ids:
        print("Cannot seed comments without users and products.")
        return
    print("Seeding comments...")
    comments_data = []
    products_to_comment = random.sample(product_ids, k=min(len(product_ids), int(len(user_ids) * 1.5)))

    for product_id in products_to_comment:
        num_comments = random.randint(num_comments_range[0], num_comments_range[1])
        possible_commenters = list(user_ids)
        if not possible_commenters: continue

        for _ in range(num_comments):
             user_id = random.choice(possible_commenters)
             text_options = [
                "Is this still available?",
                "Interested! Can we meet near the library?",
                f"What's the condition like? ({random.choice(['Any scratches?', 'Any issues?', 'Used much?'])})",
                f"Could you do ${round(random.uniform(5.0, 50.0), 2):.2f}?", # Generic lower offer
                "Is the price firm?",
                "Still for sale?",
                "I'll take it! Sent you a PM.",
                "Can I see it sometime this week?",
                f"Is this the edition required for {fake.random_element(elements=('Dr. Evans', 'Prof. Lee', 'the Bio dept'))}?",
                "Any chance you'd trade for [my item]?",
             ]
             text = random.choice(text_options)
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
        cursor.execute("SELECT COUNT(*) FROM comments")
        comment_count = cursor.fetchone()[0]
        print(f"Seeded comments. Total comments in DB: {comment_count}. (Attempted {len(comments_data)})")

    except sqlite3.Error as e:
        print(f"Error seeding comments: {e}")
        conn.rollback()

def seed_reviews(conn, user_ids, product_id_map, num_reviews_range):
    """Seeds reviews with more relevant comments based on rating."""
    if not user_ids or len(user_ids) < 2 or not product_id_map:
        print("Cannot seed reviews without at least 2 users and products.")
        return
    print("Seeding reviews...")
    reviews_data = []
    sellers = list(set(product_id_map.values()))
    potential_reviewers = list(user_ids)

    for reviewed_user_id in sellers:
        num_reviews = random.randint(num_reviews_range[0], num_reviews_range[1])
        possible_reviewers = [r for r in potential_reviewers if r != reviewed_user_id]
        if not possible_reviewers: continue

        products_by_seller = [pid for pid, sid in product_id_map.items() if sid == reviewed_user_id]
        num_reviews = min(num_reviews, len(possible_reviewers))
        reviewers_for_this_seller = random.sample(possible_reviewers, k=num_reviews)

        for reviewer_id in reviewers_for_this_seller:
            product_id = random.choice(products_by_seller) if products_by_seller and random.random() < 0.7 else None
            rating = random.randint(1, 5)
            timestamp = fake.date_time_between(start_date='-6m', end_date='now')
            comment = None
            if random.random() < 0.8:
                comment_options_positive = [
                    "Great seller! Item was exactly as described. Easy pickup.",
                    "Smooth transaction, very friendly and responsive.",
                    "Quick meet up. Item in perfect condition. Highly recommend!",
                    "Got a great deal on the textbook, super happy. Thanks!",
                    "Excellent communication, would buy from again!",
                ]
                comment_options_neutral = [
                    "Item was okay, transaction was fine.",
                    "Met up eventually. Item as described.",
                    "Standard transaction, no issues.",
                ]
                comment_options_negative = [
                    "Item wasn't quite in the condition described. Disappointed.",
                    "Seller was late and hard to reach.",
                    "Difficult to coordinate pickup. Wouldn't recommend.",
                    "Item had undisclosed damage.",
                ]
                if rating >= 4: comment = random.choice(comment_options_positive)
                elif rating == 3: comment = random.choice(comment_options_neutral)
                else: comment = random.choice(comment_options_negative)

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
        cursor.execute("SELECT COUNT(*) FROM reviews")
        review_count = cursor.fetchone()[0]
        print(f"Seeded reviews. Total reviews in DB: {review_count}. (Attempted {len(reviews_data)})")
    except sqlite3.Error as e:
        if "UNIQUE constraint failed" in str(e):
             print(f"Skipped duplicate review: {e}")
             conn.rollback()
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
        num_likes = int(len(product_ids) * like_probability * (random.random() + 0.5))
        products_liked_by_user = random.sample(product_ids, k=min(num_likes, len(product_ids)))
        for product_id in products_liked_by_user:
                timestamp = fake.date_time_between(start_date='-6m', end_date='now')
                likes_data.append((user_id, product_id, timestamp))

    if not likes_data:
        print("No likes generated.")
        return

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO likes (user_id, product_id, "timestamp")
            VALUES (?, ?, ?)
        """, likes_data)
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM likes")
        like_count = cursor.fetchone()[0]
        print(f"Seeded likes. Total likes in DB: {like_count}. (Attempted {len(likes_data)}, duplicates ignored)")
    except sqlite3.Error as e:
        print(f"Error seeding likes: {e}")
        conn.rollback()

# --- Main Execution ---
if __name__ == "__main__":
    conn = get_db_connection()
    if not conn: exit()
    start_time = datetime.now()
    print(f"\n--- Starting Database Seeding ({start_time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
    try:
        # **MODIFIED Call Order/Args**
        campus_map = seed_campuses(conn) # Returns {id: name} map
        category_map = seed_categories(conn) # Returns {id: name} map
        user_ids = seed_users(conn, NUM_USERS, campus_map) # Pass campus_map
        product_id_map = seed_products(conn, user_ids, category_map, NUM_PRODUCTS_PER_USER_RANGE) # Pass category_map
        product_ids = list(product_id_map.keys())
        if product_ids:
             seed_comments(conn, user_ids, product_ids, NUM_COMMENTS_PER_PRODUCT_RANGE)
             seed_likes(conn, user_ids, product_ids, LIKE_PROBABILITY)
        seed_reviews(conn, user_ids, product_id_map, NUM_REVIEWS_PER_USER_RANGE)
        end_time = datetime.now()
        print(f"\n--- Database seeding completed successfully ({end_time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
        print(f"--- Total time: {end_time - start_time} ---")
        print("\n--- Final Record Counts ---")
        tables_to_check = ['campuses', 'categories', 'users', 'products', 'comments', 'reviews', 'likes']
        cursor = conn.cursor()
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"- {table}: {count}")
            except sqlite3.Error as e:
                 print(f"- {table}: Error counting - {e}")

    except Exception as e:
        print(f"\n--- An error occurred during seeding: {e} ---")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")