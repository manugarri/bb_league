"""Flask application factory."""
import click
from flask import Flask, request, session
from app.config import config
from app.extensions import db, jwt, login_manager, csrf, babel


def get_locale():
    """Select the best matching language for the user."""
    # Check if user has set a preferred language in session
    if 'language' in session:
        return session['language']
    # Otherwise, use the browser's accept language header
    return request.accept_languages.best_match(['es', 'en'], default='en')


def create_app(config_name: str = "development") -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    
    # Register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.teams import teams_bp
    from app.blueprints.leagues import leagues_bp
    from app.blueprints.matches import matches_bp
    from app.blueprints.bets import bets_bp
    from app.blueprints.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(teams_bp, url_prefix="/teams")
    app.register_blueprint(leagues_bp, url_prefix="/leagues")
    app.register_blueprint(matches_bp, url_prefix="/matches")
    app.register_blueprint(bets_bp, url_prefix="/bets")
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Context processor for templates
    @app.context_processor
    def inject_locale():
        from app.utils.translations import (
            translate_race, translate_position, translate_skill, 
            translate_star_player, translate_skills_list, get_team_description
        )
        return {
            'get_locale': get_locale, 
            'languages': app.config.get('LANGUAGES', ['en']),
            'tr_race': translate_race,
            'tr_position': translate_position,
            'tr_skill': translate_skill,
            'tr_star': translate_star_player,
            'tr_skills_list': translate_skills_list,
            'get_team_desc': get_team_description,
        }
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def register_cli_commands(app: Flask) -> None:
    """Register custom CLI commands."""
    
    @app.cli.command("seed")
    @click.option("--clear", is_flag=True, help="Clear existing data before seeding")
    def seed_command(clear: bool):
        """Seed the database with Blood Bowl data."""
        from app.services.seed_data import seed_all, clear_and_reseed
        
        if clear:
            click.echo("Clearing and reseeding database...")
            clear_and_reseed()
        else:
            click.echo("Seeding database...")
            seed_all()
        click.echo("Done!")
    
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.argument("password")
    def create_admin_command(username: str, email: str, password: str):
        """Create an admin user."""
        from app.models import User
        
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            click.echo(f"Error: User with username '{username}' or email '{email}' already exists.")
            return
        
        user = User(username=username, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created successfully!")


def register_error_handlers(app: Flask) -> None:
    """Register custom error handlers."""
    from flask import render_template
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

