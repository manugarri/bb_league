"""Authentication blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from app.forms.auth import LoginForm, RegistrationForm, ProfileForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user exists
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email address already registered.", "danger")
            return render_template("auth/register.html", form=form)
        
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken.", "danger")
            return render_template("auth/register.html", form=form)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            display_name=form.display_name.data or form.username.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", form=form)
        
        if not user.is_active:
            flash("This account has been deactivated.", "danger")
            return render_template("auth/login.html", form=form)
        
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))
    
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """User logout."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile management."""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.bio = form.bio.data
        
        # Change password if provided
        if form.new_password.data:
            if not current_user.check_password(form.current_password.data):
                flash("Current password is incorrect.", "danger")
                return render_template("auth/profile.html", form=form)
            current_user.set_password(form.new_password.data)
        
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.profile"))
    
    return render_template("auth/profile.html", form=form)

