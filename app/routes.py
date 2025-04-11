from flask import Blueprint, render_template

# Using Blueprint for better organization, even for simple routes initially
bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    # Later, fetch products from DB using manual SQL via db.py helpers
    return "<h1>Welcome to the College Marketplace!</h1> (Basic Setup Complete)"
    # Replace with render_template('index.html') when template exists