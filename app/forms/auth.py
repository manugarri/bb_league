"""Authentication forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )
    remember_me = BooleanField("Remember Me")


class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    display_name = StringField(
        "Display Name",
        validators=[Optional(), Length(max=64)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )


class ProfileForm(FlaskForm):
    """User profile form."""
    display_name = StringField(
        "Display Name",
        validators=[Optional(), Length(max=64)]
    )
    bio = TextAreaField(
        "Bio",
        validators=[Optional(), Length(max=500)]
    )
    current_password = PasswordField(
        "Current Password",
        validators=[Optional()]
    )
    new_password = PasswordField(
        "New Password",
        validators=[Optional(), Length(min=8)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[EqualTo("new_password", message="Passwords must match")]
    )

