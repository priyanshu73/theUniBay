# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
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