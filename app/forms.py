# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
import sqlite3 # Needed for custom validator checking DB
from db.db import get_db # Import helper to check DB

# --- Custom Validators ---
def edu_email_required(form, field):
    """ Custom validator to check for .edu email """
    if not field.data.lower().endswith('.edu'):
        raise ValidationError('Must use a valid .edu email address.')

def email_exists(form, field):
    """ Custom validator to check if email already exists """
    try:
        db = get_db()
        cursor = db.execute('SELECT id FROM users WHERE email = ?', (field.data,))
        user = cursor.fetchone()
        if user:
            raise ValidationError('Email address already registered. Please log in.')
    except sqlite3.Error as e:
        # Log error appropriately
        print(f"Database error during email check: {e}")
        # Let it proceed for now, IntegrityError on insert will catch it ultimately
        pass # Or raise a generic validation error

# --- Forms ---
class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email (.edu)', validators=[DataRequired(), Email(), edu_email_required, email_exists])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me') # Optional for Flask-Login
    submit = SubmitField('Login')

# Add Profile Edit Form later if needed
# class EditProfileForm(FlaskForm):
#     name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
#     profile_info = TextAreaField('Profile Info', validators=[Length(max=500)])
#     submit = SubmitField('Update Profile')

# --- Product Forms ---
class ProductForm(FlaskForm):
    """Form for creating and editing products/listings"""
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=2000)])
    price = DecimalField('Price ($)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Price must be greater than $0.01')
    ], places=2)
    
    # Category dropdown - will be populated from database
    category = SelectField('Category', validators=[DataRequired()], coerce=int)
    
    # Condition dropdown with predefined choices
    condition = SelectField('Condition', validators=[DataRequired()], 
                           choices=[
                               ('new', 'New (unused)'),
                               ('like_new', 'Like New (barely used)'),
                               ('good', 'Good (some signs of use)'),
                               ('fair', 'Fair (noticeable wear)'),
                               ('poor', 'Poor (significant wear)')
                           ])
    
    # Optional image upload
    image = FileField('Upload Image (optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    
    submit = SubmitField('Post Listing')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form and populate the category dropdown from database"""
        super(ProductForm, self).__init__(*args, **kwargs)
        # Populate category choices from database
        try:
            db = get_db()
            categories = db.execute('SELECT id, name FROM categories ORDER BY name').fetchall()
            self.category.choices = [(cat['id'], cat['name']) for cat in categories]
        except (sqlite3.Error, AttributeError) as e:
            # Handle case where database might not be available during form initialization
            print(f"Error loading categories: {e}")
            # Provide empty/default choice if DB fails
            self.category.choices = [(0, 'Error loading categories')]
            

class EditProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    profile_info = TextAreaField('Profile Info', validators=[Length(max=500)])
    submit = SubmitField('Save Changes')