"""Main blueprint for home and general pages."""
from flask import Blueprint, render_template, session, redirect, request, url_for, current_app
from flask_login import current_user, login_required
from app.models import League, Match, Team

main_bp = Blueprint("main", __name__)


@main_bp.route("/set-language/<language>")
def set_language(language):
    """Set the user's preferred language."""
    if language in current_app.config.get('LANGUAGES', ['en']):
        session['language'] = language
    return redirect(request.referrer or url_for('auth.login'))


@main_bp.route("/")
@login_required
def index():
    """Home page."""
    # Get recent matches
    recent_matches = Match.query.filter_by(status="completed").order_by(
        Match.played_date.desc()
    ).limit(5).all()
    
    # Get active leagues
    active_leagues = League.query.filter(
        League.status.in_(["registration", "active"])
    ).order_by(League.created_at.desc()).limit(5).all()
    
    # Get user's teams
    user_teams = current_user.teams.limit(5).all()
    
    # Get user's scheduled matches (scheduled or in prematch phase)
    team_ids = [t.id for t in user_teams]
    scheduled_matches = []
    if team_ids:
        from sqlalchemy import or_
        scheduled_matches = Match.query.filter(
            Match.status.in_(["scheduled", "prematch"]),
            or_(Match.home_team_id.in_(team_ids), Match.away_team_id.in_(team_ids))
        ).order_by(Match.scheduled_date.asc(), Match.round_number.asc()).limit(5).all()
    
    return render_template(
        "main/index.html",
        recent_matches=recent_matches,
        active_leagues=active_leagues,
        user_teams=user_teams,
        scheduled_matches=scheduled_matches
    )


@main_bp.route("/about")
@login_required
def about():
    """About page."""
    return render_template("main/about.html")


@main_bp.route("/rules")
@login_required
def rules():
    """Blood Bowl rules reference."""
    return render_template("main/rules.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard."""
    # User's teams
    teams = current_user.teams.all()
    
    # Upcoming matches for user's teams
    team_ids = [t.id for t in teams]
    upcoming_matches = Match.query.filter(
        Match.status == "scheduled",
        (Match.home_team_id.in_(team_ids) | Match.away_team_id.in_(team_ids))
    ).order_by(Match.scheduled_date.asc()).limit(10).all()
    
    # Recent results
    recent_results = Match.query.filter(
        Match.status == "completed",
        (Match.home_team_id.in_(team_ids) | Match.away_team_id.in_(team_ids))
    ).order_by(Match.played_date.desc()).limit(5).all()
    
    return render_template(
        "main/dashboard.html",
        teams=teams,
        upcoming_matches=upcoming_matches,
        recent_results=recent_results
    )
