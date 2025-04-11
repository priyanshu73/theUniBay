import os
import sqlite3
from flask import Flask, g
from flask_login import LoginManager
from config import Config

# Initialize Flask-Login
login_manager = LoginManager()
# Redirect users to the login page if they try to access protected pages
login_manager.login_view = 'auth.login' # Assuming 'auth' blueprint and 'login' route later
login_manager.login_message_category = 'info' # Optional: flash message category

# --- Database Helper Functions ---
# Moved to db/db.py, but registration happens here

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False, instance_path=config_class.INSTANCE_FOLDER_PATH)
    app.config.from_object(config_class)

    # Ensure the instance folder exists (moved path definition to Config)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass # Already handled in Config, but good practice

    # Initialize Flask extensions
    login_manager.init_app(app)

    # Initialize Database utilities
    from db import db as db_module
    db_module.init_app(app) # Register db commands and teardown

    # Register Blueprints (We'll create these later)
    # Example: from app.routes import bp as main_bp
    # app.register_blueprint(main_bp)

    # Placeholder for main routes for now
    from . import routes
    app.register_blueprint(routes.bp)

    # Placeholder for auth routes
    # from . import auth
    # app.register_blueprint(auth.bp, url_prefix='/auth')

    print(f"App created with instance path: {app.instance_path}")
    print(f"Database path from config: {app.config['DATABASE']}")

    return app