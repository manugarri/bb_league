"""Leagues blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_babel import get_locale
from flask_login import login_required, current_user
from app.extensions import db
from app.models import League, Season, LeagueTeam, Standing, Match, Team
from app.forms.league import CreateLeagueForm, EditLeagueForm, JoinLeagueForm, ScheduleMatchForm
from app.services.scheduler import generate_round_robin_schedule

leagues_bp = Blueprint("leagues", __name__)


@leagues_bp.route("/")
@login_required
def index():
    """List all leagues."""
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "")
    
    query = League.query.filter_by(is_public=True)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if search:
        query = query.filter(League.name.ilike(f"%{search}%"))
    
    leagues = query.order_by(League.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template(
        "leagues/index.html",
        leagues=leagues,
        current_status=status_filter,
        search=search
    )


@leagues_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new league (admin only)."""
    if not current_user.is_admin:
        if str(get_locale()) == 'es':
            flash("Solo los administradores pueden crear ligas.", "danger")
        else:
            flash("Only administrators can create leagues.", "danger")
        return redirect(url_for("leagues.index"))
    
    form = CreateLeagueForm()
    
    if form.validate_on_submit():
        league = League(
            name=form.name.data,
            commissioner_id=current_user.id,
            description=form.description.data,
            format=form.format.data,
            max_teams=form.max_teams.data,
            min_teams=form.min_teams.data,
            starting_treasury=form.starting_treasury.data,
            win_points=form.win_points.data,
            draw_points=form.draw_points.data,
            loss_points=form.loss_points.data,
            min_roster_size=form.min_roster_size.data,
            max_roster_size=form.max_roster_size.data,
            allow_star_players=form.allow_star_players.data,
            is_public=form.is_public.data
        )
        
        db.session.add(league)
        db.session.commit()
        
        # Create initial season
        season = Season(
            league_id=league.id,
            name="Season 1",
            number=1
        )
        db.session.add(season)
        db.session.commit()
        
        if str(get_locale()) == 'es':
            flash(f"¡Liga '{league.name}' creada correctamente!", "success")
        else:
            flash(f"League '{league.name}' created successfully!", "success")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    return render_template("leagues/create.html", form=form)


@leagues_bp.route("/<int:league_id>")
@login_required
def view(league_id: int):
    """View league details."""
    league = League.query.get_or_404(league_id)
    
    # Get registered teams
    league_teams = league.teams.filter_by(is_approved=True).all()
    teams = [lt.team for lt in league_teams]
    
    # Get pending teams (for commissioner)
    pending_teams = []
    if current_user.is_authenticated and current_user.id == league.commissioner_id:
        pending = league.teams.filter_by(is_approved=False).all()
        pending_teams = [lt.team for lt in pending]
    
    # Get standings
    standings = []
    if league.current_season:
        standings = Standing.query.filter_by(
            season_id=league.current_season.id
        ).order_by(Standing.points.desc(), Standing.touchdowns_for.desc()).all()
    
    # Get recent matches
    recent_matches = league.matches.filter_by(
        status="completed"
    ).order_by(Match.played_date.desc()).limit(10).all()
    
    # Get upcoming matches
    upcoming_matches = league.matches.filter_by(
        status="scheduled"
    ).order_by(Match.scheduled_date.asc()).limit(10).all()
    
    # Check if user can join
    user_teams = []
    can_join = False
    if current_user.is_authenticated:
        user_teams = current_user.teams.filter_by(is_active=True).all()
        # Filter out teams already in the league
        registered_team_ids = [lt.team_id for lt in league.teams.all()]
        user_teams = [t for t in user_teams if t.id not in registered_team_ids]
        can_join = league.can_register() and len(user_teams) > 0
    
    is_commissioner = current_user.is_authenticated and current_user.id == league.commissioner_id
    
    return render_template(
        "leagues/view.html",
        league=league,
        teams=teams,
        standings=standings,
        recent_matches=recent_matches,
        upcoming_matches=upcoming_matches,
        pending_teams=pending_teams,
        user_teams=user_teams,
        can_join=can_join,
        is_commissioner=is_commissioner
    )


@leagues_bp.route("/<int:league_id>/edit", methods=["GET", "POST"])
@login_required
def edit(league_id: int):
    """Edit league settings."""
    league = League.query.get_or_404(league_id)
    
    if league.commissioner_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = EditLeagueForm(obj=league)
    
    if form.validate_on_submit():
        league.name = form.name.data
        league.description = form.description.data
        league.max_teams = form.max_teams.data
        league.min_roster_size = form.min_roster_size.data
        league.max_roster_size = form.max_roster_size.data
        league.allow_star_players = form.allow_star_players.data
        league.is_public = form.is_public.data
        league.registration_open = form.registration_open.data
        
        db.session.commit()
        if str(get_locale()) == 'es':
            flash("Liga actualizada correctamente.", "success")
        else:
            flash("League updated successfully.", "success")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    return render_template("leagues/edit.html", form=form, league=league)


@leagues_bp.route("/<int:league_id>/delete", methods=["POST"])
@login_required
def delete(league_id: int):
    """Delete a league (admin only)."""
    if not current_user.is_admin:
        abort(403)
    
    league = League.query.get_or_404(league_id)
    league_name = league.name
    
    # Get language for flash messages
    from flask import session
    lang = session.get('language', 'en')
    
    # Delete the league (cascade will handle teams, matches, etc.)
    db.session.delete(league)
    db.session.commit()
    
    if lang == 'es':
        flash(f"Liga '{league_name}' eliminada correctamente.", "success")
    else:
        flash(f"League '{league_name}' deleted successfully.", "success")
    
    return redirect(url_for("leagues.index"))


@leagues_bp.route("/<int:league_id>/join", methods=["POST"])
@login_required
def join(league_id: int):
    """Join a league with a team."""
    league = League.query.get_or_404(league_id)
    
    if not league.can_register():
        if str(get_locale()) == 'es':
            flash("Esta liga no acepta inscripciones.", "warning")
        else:
            flash("This league is not accepting registrations.", "warning")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    team_id = request.form.get("team_id", type=int)
    team = Team.query.get_or_404(team_id)
    
    # Allow team coach or admin to join
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Check if team is already registered
    existing = LeagueTeam.query.filter_by(league_id=league.id, team_id=team.id).first()
    if existing:
        if str(get_locale()) == 'es':
            flash("Este equipo ya está registrado en esta liga.", "warning")
        else:
            flash("This team is already registered in this league.", "warning")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    # Validate roster rules
    roster_count = team.roster_count
    min_roster = league.min_roster_size or 11
    max_roster = league.max_roster_size or 16
    
    from flask import session
    lang = session.get('language', 'en')
    
    if roster_count < min_roster:
        if lang == 'es':
            flash(f"El equipo necesita al menos {min_roster} jugadores para unirse a esta liga. Plantilla actual: {roster_count}.", "danger")
        else:
            flash(f"Team needs at least {min_roster} players to join this league. Current roster: {roster_count}.", "danger")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    if roster_count > max_roster:
        if lang == 'es':
            flash(f"El equipo excede el tamaño máximo de plantilla de {max_roster} jugadores. Plantilla actual: {roster_count}.", "danger")
        else:
            flash(f"Team exceeds the maximum roster size of {max_roster} players. Current roster: {roster_count}.", "danger")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    # Register team
    league_team = LeagueTeam(
        league_id=league.id,
        team_id=team.id,
        is_approved=False  # Requires commissioner approval
    )
    db.session.add(league_team)
    db.session.commit()
    
    if str(get_locale()) == 'es':
        flash(f"¡Equipo '{team.name}' registrado! Esperando aprobación del comisionado.", "success")
    else:
        flash(f"Team '{team.name}' registered! Awaiting commissioner approval.", "success")
    return redirect(url_for("leagues.view", league_id=league.id))


@leagues_bp.route("/<int:league_id>/approve/<int:team_id>", methods=["POST"])
@login_required
def approve_team(league_id: int, team_id: int):
    """Approve a team's registration (commissioner only)."""
    league = League.query.get_or_404(league_id)
    
    if league.commissioner_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    league_team = LeagueTeam.query.filter_by(
        league_id=league.id,
        team_id=team_id
    ).first_or_404()
    
    league_team.is_approved = True
    league_team.approved_at = db.func.now()
    
    # Create standing entry
    if league.current_season:
        standing = Standing(
            season_id=league.current_season.id,
            team_id=team_id
        )
        db.session.add(standing)
    
    db.session.commit()
    
    if str(get_locale()) == 'es':
        flash("¡Equipo aprobado!", "success")
    else:
        flash("Team approved!", "success")
    return redirect(url_for("leagues.view", league_id=league.id))


@leagues_bp.route("/<int:league_id>/reject/<int:team_id>", methods=["POST"])
@login_required
def reject_team(league_id: int, team_id: int):
    """Reject a team's registration (commissioner only)."""
    league = League.query.get_or_404(league_id)
    
    if league.commissioner_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    league_team = LeagueTeam.query.filter_by(
        league_id=league.id,
        team_id=team_id
    ).first_or_404()
    
    db.session.delete(league_team)
    db.session.commit()
    
    if str(get_locale()) == 'es':
        flash("Inscripción de equipo rechazada.", "warning")
    else:
        flash("Team registration rejected.", "warning")
    return redirect(url_for("leagues.view", league_id=league.id))


@leagues_bp.route("/<int:league_id>/generate-schedule", methods=["POST"])
@login_required
def generate_schedule(league_id: int):
    """Generate match schedule for the league."""
    league = League.query.get_or_404(league_id)
    
    if league.commissioner_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Get approved teams
    league_teams = league.teams.filter_by(is_approved=True).all()
    teams = [lt.team for lt in league_teams]
    
    if len(teams) < league.min_teams:
        if str(get_locale()) == 'es':
            flash(f"Se necesitan al menos {league.min_teams} equipos para generar el calendario.", "warning")
        else:
            flash(f"Need at least {league.min_teams} teams to generate schedule.", "warning")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    # Generate schedule based on format
    if league.format == "round_robin":
        schedule = generate_round_robin_schedule(teams)
    else:
        if str(get_locale()) == 'es':
            flash("La generación de calendario para este formato aún no está implementada.", "warning")
        else:
            flash("Schedule generation for this format not yet implemented.", "warning")
        return redirect(url_for("leagues.view", league_id=league.id))
    
    # Create matches
    season = league.current_season
    for round_num, matches in enumerate(schedule, 1):
        for home_team, away_team in matches:
            match = Match(
                league_id=league.id,
                season_id=season.id if season else None,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                round_number=round_num,
                status="scheduled"
            )
            db.session.add(match)
    
    # Update season
    if season:
        season.total_rounds = len(schedule)
    
    # Update league status
    league.status = "active"
    league.registration_open = False
    
    db.session.commit()
    
    match_count = sum(len(r) for r in schedule)
    if str(get_locale()) == 'es':
        flash(f"¡Calendario generado! {match_count} partidos creados.", "success")
    else:
        flash(f"Schedule generated! {match_count} matches created.", "success")
    return redirect(url_for("leagues.view", league_id=league.id))


@leagues_bp.route("/<int:league_id>/standings")
@login_required
def standings(league_id: int):
    """View full standings table."""
    league = League.query.get_or_404(league_id)
    
    standings = []
    if league.current_season:
        standings = Standing.query.filter_by(
            season_id=league.current_season.id
        ).order_by(
            Standing.points.desc(),
            Standing.touchdowns_for.desc(),
            Standing.casualties_inflicted.desc()
        ).all()
        
        # Add rank
        for i, standing in enumerate(standings, 1):
            standing.rank = i
    
    return render_template(
        "leagues/standings.html",
        league=league,
        standings=standings
    )


@leagues_bp.route("/<int:league_id>/schedule")
@login_required
def schedule(league_id: int):
    """View full match schedule."""
    league = League.query.get_or_404(league_id)
    
    # Group matches by round
    matches_by_round = {}
    for match in league.matches.order_by(Match.round_number, Match.id).all():
        round_num = match.round_number or 0
        if round_num not in matches_by_round:
            matches_by_round[round_num] = []
        matches_by_round[round_num].append(match)
    
    # Get approved teams for the add match form (admin only)
    league_teams = []
    form = None
    if current_user.is_admin:
        league_teams_entries = league.teams.filter_by(is_approved=True).all()
        league_teams = [(lt.team.id, lt.team.name) for lt in league_teams_entries]
        form = ScheduleMatchForm()
        form.home_team_id.choices = league_teams
        form.away_team_id.choices = league_teams
    
    return render_template(
        "leagues/schedule.html",
        league=league,
        matches_by_round=matches_by_round,
        form=form,
        league_teams=league_teams
    )


@leagues_bp.route("/<int:league_id>/schedule/add", methods=["POST"])
@login_required
def add_match(league_id: int):
    """Add a new scheduled match (admin only)."""
    if not current_user.is_admin:
        abort(403)
    
    league = League.query.get_or_404(league_id)
    lang = session.get('language', 'en')
    
    # Get form data
    home_team_id = request.form.get("home_team_id", type=int)
    away_team_id = request.form.get("away_team_id", type=int)
    round_number = request.form.get("round_number", type=int, default=1)
    
    # Validate teams exist and are in the league
    home_team = Team.query.get_or_404(home_team_id)
    away_team = Team.query.get_or_404(away_team_id)
    
    home_in_league = LeagueTeam.query.filter_by(
        league_id=league.id, team_id=home_team_id, is_approved=True
    ).first()
    away_in_league = LeagueTeam.query.filter_by(
        league_id=league.id, team_id=away_team_id, is_approved=True
    ).first()
    
    if not home_in_league or not away_in_league:
        if lang == 'es':
            flash("Uno o ambos equipos no están registrados en esta liga.", "danger")
        else:
            flash("One or both teams are not registered in this league.", "danger")
        return redirect(url_for("leagues.schedule", league_id=league.id))
    
    # Validate teams are different
    if home_team_id == away_team_id:
        if lang == 'es':
            flash("El equipo local y visitante deben ser diferentes.", "danger")
        else:
            flash("Home and away teams must be different.", "danger")
        return redirect(url_for("leagues.schedule", league_id=league.id))
    
    # Create the match
    match = Match(
        league_id=league.id,
        season_id=league.current_season.id if league.current_season else None,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        round_number=round_number,
        status="scheduled"
    )
    db.session.add(match)
    db.session.commit()
    
    if lang == 'es':
        flash(f"Partido añadido: {home_team.name} vs {away_team.name}", "success")
    else:
        flash(f"Match added: {home_team.name} vs {away_team.name}", "success")
    
    return redirect(url_for("leagues.schedule", league_id=league.id))


@leagues_bp.route("/<int:league_id>/schedule/<int:match_id>/delete", methods=["POST"])
@login_required
def delete_match(league_id: int, match_id: int):
    """Delete a scheduled match (admin only)."""
    if not current_user.is_admin:
        abort(403)
    
    league = League.query.get_or_404(league_id)
    match = Match.query.get_or_404(match_id)
    lang = session.get('language', 'en')
    
    # Verify match belongs to this league
    if match.league_id != league.id:
        abort(404)
    
    # Only allow deletion of scheduled (not completed) matches
    if match.status == "completed":
        if lang == 'es':
            flash("No se puede eliminar un partido completado.", "danger")
        else:
            flash("Cannot delete a completed match.", "danger")
        return redirect(url_for("leagues.schedule", league_id=league.id))
    
    match_name = f"{match.home_team.name} vs {match.away_team.name}"
    
    # Delete the match
    db.session.delete(match)
    db.session.commit()
    
    if lang == 'es':
        flash(f"Partido eliminado: {match_name}", "success")
    else:
        flash(f"Match deleted: {match_name}", "success")
    
    return redirect(url_for("leagues.schedule", league_id=league.id))

