-- Drop tables if they exist (optional, useful for re-running init-db)
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS categories;
-- Add other DROP TABLE statements here...

-- Add CREATE TABLE statements here later in Phase 1 / Phase 2
-- Example:
-- CREATE TABLE users (
--   id INTEGER PRIMARY KEY AUTOINCREMENT,
--   name TEXT NOT NULL,
--   email TEXT UNIQUE NOT NULL,
--   password_hash TEXT NOT NULL,
--   join_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );

-- CREATE TABLE categories (
--   id INTEGER PRIMARY KEY AUTOINCREMENT,
--   name TEXT UNIQUE NOT NULL
-- );

-- ... other tables (Products, Comments, Likes, Reviews etc.)