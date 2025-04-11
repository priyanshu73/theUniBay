import os
import sqlite3
from flask import Flask, g
from flask_login import LoginManager
from config import Config

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Assuming 'auth' blueprint and 'login' route later
login_manager.login_message_category = 'info' # Optional: flash message category

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False, instance_path=config_class.INSTANCE_FOLDER_PATH)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize Flask extensions
    login_manager.init_app(app)

    # Initialize Database utilities
    # --- THIS IS THE CORRECTED LINE ---
    from db import db as db_module
    # --- END CORRECTION ---
    db_module.init_app(app) # Register db commands and teardown

    # Register Blueprints
    from . import routes
    app.register_blueprint(routes.bp)

    # Placeholder for auth routes (adjust name if needed)
    # from . import auth
    # if hasattr(auth, 'bp'): # Check if auth blueprint exists before registering
    #    app.register_blueprint(auth.bp, url_prefix='/auth')

    print(f"App created with instance path: {app.instance_path}")
    print(f"Database path from config: {app.config['DATABASE']}")

    return app