
import os
import sqlite3
from flask import Flask, g
from flask_login import LoginManager
from config import Config
from db import db as db_module


login_manager = LoginManager()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False, instance_path=config_class.INSTANCE_FOLDER_PATH)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

   
    login_manager.init_app(app)

   
    db_module.init_app(app)

   
    from . import routes as main_routes
    app.register_blueprint(main_routes.bp)

   
    from . import auth
    app.register_blueprint(auth.bp)

   
    from app import product
    app.register_blueprint(product.bp)
    

    print(f"App created with instance path: {app.instance_path}")
    print(f"Database path from config: {app.config['DATABASE']}")

    return app