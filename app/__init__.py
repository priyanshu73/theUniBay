# app/__init__.py
import os
import sqlite3
from flask import Flask, g
from flask_login import LoginManager
from config import Config
from db import db as db_module # Corrected import

# --- KEEP login_manager initialization at module level ---
login_manager = LoginManager()
# --- Configure login_view using the blueprint name 'auth' ---
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.' # Customize message
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False, instance_path=config_class.INSTANCE_FOLDER_PATH)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize Flask extensions
    login_manager.init_app(app) # Initialize LoginManager with the app

    # Initialize Database utilities
    db_module.init_app(app) # Register db commands and teardown

    # --- Register Blueprints ---
    from . import routes as main_routes # Alias to avoid name clash
    app.register_blueprint(main_routes.bp)

    # --- Import and Register Auth Blueprint ---
    from . import auth
    app.register_blueprint(auth.bp) # url_prefix='/auth' is defined in auth.py

    # Register other blueprints (e.g., products) later

    print(f"App created with instance path: {app.instance_path}")
    print(f"Database path from config: {app.config['DATABASE']}")

    return app