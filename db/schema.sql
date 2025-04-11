-- Drop tables in reverse order of dependency to avoid foreign key errors
DROP TABLE IF EXISTS likes;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS product_images;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS campuses;

-- Create tables

CREATE TABLE campuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    state TEXT NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL, -- Add CHECK constraint for .edu later if desired in application logic
    password_hash TEXT NOT NULL,
    join_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    profile_info TEXT,
    campus_id INTEGER, -- Optional: Link user to a specific campus
    FOREIGN KEY (campus_id) REFERENCES campuses (id)
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0), -- Use REAL for potential decimal values
    condition TEXT, -- e.g., 'New', 'Used - Like New', 'Used - Good'
    post_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'sold', 'removed')),
    -- image_url TEXT, -- If storing only one primary image URL directly
    FOREIGN KEY (seller_id) REFERENCES users (id) ON DELETE CASCADE, -- If user deleted, remove their products
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL -- If category deleted, keep product but unlink category
);

CREATE TABLE product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    image_url TEXT NOT NULL, -- Path to the uploaded image file
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE -- Delete images if product is deleted
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE, -- Delete comment if user is deleted
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE -- Delete comment if product is deleted
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER NOT NULL,
    reviewed_user_id INTEGER NOT NULL, -- The seller being reviewed
    product_id INTEGER, -- Optional: Link review to a specific product/transaction
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL, -- Keep review if product deleted
    CHECK (reviewer_id != reviewed_user_id) -- Ensure users cannot review themselves
);

CREATE TABLE likes (
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, product_id), -- Composite key prevents duplicate likes
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

-- Optional: Add Indexes for faster lookups on frequently queried columns
CREATE INDEX idx_products_seller ON products (seller_id);
CREATE INDEX idx_products_category ON products (category_id);
CREATE INDEX idx_comments_product ON comments (product_id);
CREATE INDEX idx_reviews_reviewed_user ON reviews (reviewed_user_id);
CREATE INDEX idx_likes_product ON likes (product_id);