import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DATABASE = os.path.join(basedir, os.environ.get('DATABASE_URL') or 'instance/default.sqlite')
    # Ensure the instance folder exists if using it for the DB
    INSTANCE_FOLDER_PATH = os.path.join(basedir, 'instance')
    try:
        os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)
    except OSError as e:
        print(f"Error creating instance folder: {e}")

    # Add other configurations if needed later
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads') # Example for image uploads
    os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Create upload folder if it doesn't exist