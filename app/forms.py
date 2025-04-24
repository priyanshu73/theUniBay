# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
import sqlite3
from db.db import get_db

def edu_email_required(form, field):
    if not field.data.lower().endswith('.edu'):
        raise ValidationError('Must use a valid .edu email address.')

def email_exists(form, field):
    try:
        db = get_db()
        cursor = db.execute('SELECT id FROM users WHERE email = ?', (field.data,))
        user = cursor.fetchone()
        if user:
            raise ValidationError('Email address already registered. Please log in.')
    except sqlite3.Error as e:
        print(f"Database error during email check: {e}")
        pass

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email (.edu)', validators=[DataRequired(), Email(), edu_email_required, email_exists])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProductForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=2000)])
    price = DecimalField('Price ($)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Price must be greater than $0.01')
    ], places=2)
    category = SelectField('Category', validators=[DataRequired()], coerce=int)
    condition = SelectField('Condition', validators=[DataRequired()],
                           choices=[
                               ('new', 'New (unused)'),
                               ('like_new', 'Like New (barely used)'),
                               ('good', 'Good (some signs of use)'),
                               ('fair', 'Fair (noticeable wear)'),
                               ('poor', 'Poor (significant wear)')
                           ])
    image = FileField('Upload Image (optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Post Listing')

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        try:
            db = get_db()
            categories = db.execute('SELECT id, name FROM categories ORDER BY name').fetchall()
            self.category.choices = [(cat['id'], cat['name']) for cat in categories]
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error loading categories: {e}")
            self.category.choices = [(0, 'Error loading categories')]

class EditProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    profile_info = TextAreaField('Profile Info', validators=[Length(max=500)])
    campus_id = SelectField('Campus', coerce=int, validators=[DataRequired(message="Please select your campus.")]) # Made campus required
    submit = SubmitField('Save Changes')

    # Add validation to prevent selecting the placeholder value if needed
    def validate_campus_id(self, field):
        if field.data == 0: # Assuming 0 is your placeholder value ID
            raise ValidationError('Please select a valid campus.')