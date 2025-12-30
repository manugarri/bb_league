"""Teams blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_babel import get_locale
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Team, Race, Position, Player, Skill, PlayerSkill
from app.forms.team import CreateTeamForm, HirePlayerForm, EditTeamForm, EditPlayerForm
from app.utils.translations import translate_league_type

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/")
@login_required
def index():
    """List all teams."""
    page = request.args.get("page", 1, type=int)
    race_filter = request.args.get("race", type=int)
    search = request.args.get("search", "")
    
    query = Team.query.filter_by(is_active=True)
    
    if race_filter:
        query = query.filter_by(race_id=race_filter)
    
    if search:
        query = query.filter(Team.name.ilike(f"%{search}%"))
    
    teams = query.order_by(Team.name).paginate(page=page, per_page=20)
    races = Race.query.order_by(Race.name).all()
    
    return render_template(
        "teams/index.html", 
        teams=teams, 
        races=races,
        current_race=race_filter,
        search=search
    )


@teams_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new team."""
    form = CreateTeamForm()
    races = Race.query.order_by(Race.name).all()
    form.race_id.choices = [(r.id, r.name) for r in races]
    
    # Build league_types data for JavaScript
    race_league_types = {r.id: r.get_league_types() for r in races}
    
    # Build all possible league types for form validation (with translated labels)
    all_league_types = set()
    for r in races:
        all_league_types.update(r.get_league_types())
    select_label = "-- Selecciona Tipo de Liga (Opcional) --" if str(get_locale()) == 'es' else "-- Select League Type (Optional) --"
    form.league_type.choices = [("", select_label)] + [(lt, translate_league_type(lt)) for lt in sorted(all_league_types)]
    
    # Build translations map for JavaScript
    league_type_translations = {lt: translate_league_type(lt) for lt in all_league_types}
    
    if form.validate_on_submit():
        treasury = form.treasury.data if form.treasury.data is not None else 1000000
        league_type = form.league_type.data if form.league_type.data else None
        team = Team(
            name=form.name.data,
            coach_id=current_user.id,
            race_id=form.race_id.data,
            league_type=league_type,
            treasury=treasury
        )
        db.session.add(team)
        db.session.commit()
        
        if str(get_locale()) == 'es':
            flash(f"¡Equipo '{team.name}' creado correctamente!", "success")
        else:
            flash(f"Team '{team.name}' created successfully!", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    return render_template("teams/create.html", form=form, races=races, race_league_types=race_league_types, league_type_translations=league_type_translations)


@teams_bp.route("/<int:team_id>")
@login_required
def view(team_id: int):
    """View team details."""
    team = Team.query.get_or_404(team_id)
    players = team.players.filter_by(is_active=True).order_by(Player.number).all()
    
    # Get available positions for hiring
    positions = Position.query.filter_by(race_id=team.race_id).order_by(Position.name).all()
    
    # Check position limits
    position_counts = {}
    for p in players:
        position_counts[p.position_id] = position_counts.get(p.position_id, 0) + 1
    
    available_positions = []
    for pos in positions:
        current_count = position_counts.get(pos.id, 0)
        if current_count < pos.max_count:
            available_positions.append(pos)
    
    # Admins can manage any team
    is_owner = current_user.is_authenticated and (current_user.id == team.coach_id or current_user.is_admin)
    
    return render_template(
        "teams/view.html",
        team=team,
        players=players,
        positions=available_positions,
        position_counts=position_counts,
        is_owner=is_owner
    )


@teams_bp.route("/<int:team_id>/edit", methods=["GET", "POST"])
@login_required
def edit(team_id: int):
    """Edit team details."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = EditTeamForm(obj=team)
    
    # Set league_type choices based on team's race (with translated labels)
    league_types = team.race.get_league_types()
    none_label = "-- Ninguno --" if str(get_locale()) == 'es' else "-- None --"
    form.league_type.choices = [("", none_label)] + [(lt, translate_league_type(lt)) for lt in league_types]
    
    if form.validate_on_submit():
        team.name = form.name.data
        team.league_type = form.league_type.data if form.league_type.data else None
        if form.treasury.data is not None:
            team.treasury = form.treasury.data
        # Update team assets
        if form.rerolls.data is not None:
            team.rerolls = form.rerolls.data
        if form.assistant_coaches.data is not None:
            team.assistant_coaches = form.assistant_coaches.data
        if form.cheerleaders.data is not None:
            team.cheerleaders = form.cheerleaders.data
        team.has_apothecary = form.has_apothecary.data
        if form.fan_factor.data is not None:
            team.fan_factor = form.fan_factor.data
        # Recalculate team value
        team.calculate_tv()
        db.session.commit()
        if str(get_locale()) == 'es':
            flash("Equipo actualizado correctamente.", "success")
        else:
            flash("Team updated successfully.", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    return render_template("teams/edit.html", form=form, team=team)


@teams_bp.route("/<int:team_id>/delete", methods=["POST"])
@login_required
def delete(team_id: int):
    """Delete a team (admin only)."""
    if not current_user.is_admin:
        abort(403)
    
    team = Team.query.get_or_404(team_id)
    team_name = team.name
    
    # Get language for flash messages
    lang = session.get('language', 'en')
    
    # Delete the team (cascade will handle players, etc.)
    db.session.delete(team)
    db.session.commit()
    
    if lang == 'es':
        flash(f"Equipo '{team_name}' eliminado correctamente.", "success")
    else:
        flash(f"Team '{team_name}' deleted successfully.", "success")
    
    return redirect(url_for("teams.index"))


@teams_bp.route("/<int:team_id>/hire", methods=["GET", "POST"])
@login_required
def hire_player(team_id: int):
    """Hire a new player."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = HirePlayerForm()
    positions = Position.query.filter_by(race_id=team.race_id).order_by(Position.name).all()
    form.position_id.choices = [(p.id, f"{p.name} ({p.cost:,}g)") for p in positions]
    
    if form.validate_on_submit():
        position = Position.query.get(form.position_id.data)
        
        # Check treasury
        if team.treasury < position.cost:
            if str(get_locale()) == 'es':
                flash("¡No hay suficiente oro en la tesorería!", "danger")
            else:
                flash("Not enough gold in treasury!", "danger")
            return render_template("teams/hire_player.html", form=form, team=team)
        
        # Check roster limit
        if team.roster_count >= 16:
            if str(get_locale()) == 'es':
                flash("¡Plantilla completa! Máximo 16 jugadores.", "danger")
            else:
                flash("Roster is full! Maximum 16 players.", "danger")
            return render_template("teams/hire_player.html", form=form, team=team)
        
        # Check position limit
        current_count = team.players.filter_by(position_id=position.id, is_active=True).count()
        if current_count >= position.max_count:
            if str(get_locale()) == 'es':
                flash(f"Máximo {position.max_count} {position.name}(s) permitido(s).", "danger")
            else:
                flash(f"Maximum {position.max_count} {position.name}(s) allowed.", "danger")
            return render_template("teams/hire_player.html", form=form, team=team)
        
        # Create player
        player = Player(
            team_id=team.id,
            position_id=position.id,
            name=form.name.data,
            number=form.number.data,
            # Initialize stats from position
            movement=position.movement,
            strength=position.strength,
            agility=position.agility,
            passing=position.passing,
            armor=position.armor,
            value=position.cost
        )
        
        # Deduct cost
        team.treasury -= position.cost
        
        db.session.add(player)
        db.session.commit()
        
        # Update team value
        team.calculate_tv()
        db.session.commit()
        
        if str(get_locale()) == 'es':
            flash(f"¡Jugador '{player.name}' contratado correctamente!", "success")
        else:
            flash(f"Player '{player.name}' hired successfully!", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    return render_template("teams/hire_player.html", form=form, team=team, positions=positions)


@teams_bp.route("/<int:team_id>/player/<int:player_id>")
@login_required
def view_player(team_id: int, player_id: int):
    """View player details."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    
    if player.team_id != team.id:
        abort(404)
    
    # Get match history
    match_stats = player.match_stats.order_by(player.match_stats.c.id.desc()).limit(10).all() if hasattr(player.match_stats, 'c') else player.match_stats.limit(10).all()
    
    # Admins can manage any team
    is_owner = current_user.is_authenticated and (current_user.id == team.coach_id or current_user.is_admin)
    
    return render_template(
        "teams/player.html",
        team=team,
        player=player,
        match_stats=match_stats,
        is_owner=is_owner
    )


@teams_bp.route("/<int:team_id>/player/<int:player_id>/edit", methods=["GET", "POST"])
@login_required
def edit_player(team_id: int, player_id: int):
    """Edit player details."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    
    if player.team_id != team.id:
        abort(404)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = EditPlayerForm(obj=player)
    
    if form.validate_on_submit():
        player.name = form.name.data
        player.number = form.number.data
        db.session.commit()
        if str(get_locale()) == 'es':
            flash("Jugador actualizado correctamente.", "success")
        else:
            flash("Player updated successfully.", "success")
        return redirect(url_for("teams.view_player", team_id=team.id, player_id=player.id))
    
    # Get player's current skills
    current_skills = player.skills.all()
    current_skill_ids = [ps.skill_id for ps in current_skills]
    
    # Get available skills based on position's skill access
    position = player.position
    primary_categories = list(position.primary_skills or "")
    secondary_categories = list(position.secondary_skills or "")
    all_categories = primary_categories + secondary_categories
    
    # Query available skills (not already learned)
    available_skills = Skill.query.filter(
        Skill.category.in_(all_categories),
        ~Skill.id.in_(current_skill_ids) if current_skill_ids else True
    ).order_by(Skill.category, Skill.name).all()
    
    # Organize by category for display
    skills_by_category = {}
    for skill in available_skills:
        cat = skill.category
        if cat not in skills_by_category:
            skills_by_category[cat] = {
                'name': skill.category_name,
                'name_es': skill.category_name_es,
                'is_primary': cat in primary_categories,
                'skills': []
            }
        skills_by_category[cat]['skills'].append(skill)
    
    return render_template(
        "teams/edit_player.html",
        form=form,
        team=team,
        player=player,
        current_skills=current_skills,
        skills_by_category=skills_by_category,
        primary_categories=primary_categories,
        secondary_categories=secondary_categories
    )


@teams_bp.route("/<int:team_id>/player/<int:player_id>/fire", methods=["POST"])
@login_required
def fire_player(team_id: int, player_id: int):
    """Fire (release) a player."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    
    if player.team_id != team.id:
        abort(404)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    player.is_active = False
    db.session.commit()
    
    team.calculate_tv()
    db.session.commit()
    
    if str(get_locale()) == 'es':
        flash(f"Jugador '{player.name}' ha sido liberado.", "warning")
    else:
        flash(f"Player '{player.name}' has been released.", "warning")
    return redirect(url_for("teams.view", team_id=team.id))


@teams_bp.route("/<int:team_id>/player/<int:player_id>/add-skill/<int:skill_id>", methods=["POST"])
@login_required
def add_player_skill(team_id: int, player_id: int, skill_id: int):
    """Add a skill to a player."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    skill = Skill.query.get_or_404(skill_id)
    
    if player.team_id != team.id:
        abort(404)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    lang = session.get('language', 'en')
    
    # Check if player already has this skill
    existing = PlayerSkill.query.filter_by(player_id=player.id, skill_id=skill.id).first()
    if existing:
        if lang == 'es':
            flash(f"{player.name} ya tiene la habilidad {skill.name_es or skill.name}.", "warning")
        else:
            flash(f"{player.name} already has the skill {skill.name}.", "warning")
        return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))
    
    # Verify skill category is accessible to this position
    position = player.position
    primary_categories = list(position.primary_skills or "")
    secondary_categories = list(position.secondary_skills or "")
    all_categories = primary_categories + secondary_categories
    
    if skill.category not in all_categories:
        if lang == 'es':
            flash(f"Esta posición no puede aprender habilidades de {skill.category_name_es}.", "danger")
        else:
            flash(f"This position cannot learn {skill.category_name} skills.", "danger")
        return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))
    
    # Add the skill
    player_skill = PlayerSkill(
        player_id=player.id,
        skill_id=skill.id,
        is_starting=False
    )
    db.session.add(player_skill)
    
    # Update player value (skills add 20,000 to player value)
    player.calculate_value()
    team.calculate_tv()
    db.session.commit()
    
    skill_display = skill.name_es if lang == 'es' and skill.name_es else skill.name
    if lang == 'es':
        flash(f"¡Habilidad '{skill_display}' añadida a {player.name}!", "success")
    else:
        flash(f"Skill '{skill.name}' added to {player.name}!", "success")
    
    return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))


@teams_bp.route("/<int:team_id>/player/<int:player_id>/remove-skill/<int:skill_id>", methods=["POST"])
@login_required
def remove_player_skill(team_id: int, player_id: int, skill_id: int):
    """Remove a skill from a player."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    skill = Skill.query.get_or_404(skill_id)
    
    if player.team_id != team.id:
        abort(404)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    lang = session.get('language', 'en')
    
    # Find the player skill
    player_skill = PlayerSkill.query.filter_by(player_id=player.id, skill_id=skill.id).first()
    
    if not player_skill:
        if lang == 'es':
            flash(f"{player.name} no tiene la habilidad {skill.name_es or skill.name}.", "warning")
        else:
            flash(f"{player.name} doesn't have the skill {skill.name}.", "warning")
        return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))
    
    # Cannot remove starting skills
    if player_skill.is_starting:
        if lang == 'es':
            flash("No se pueden eliminar las habilidades iniciales.", "danger")
        else:
            flash("Cannot remove starting skills.", "danger")
        return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))
    
    # Remove the skill
    db.session.delete(player_skill)
    
    # Update player value
    player.calculate_value()
    team.calculate_tv()
    db.session.commit()
    
    skill_display = skill.name_es if lang == 'es' and skill.name_es else skill.name
    if lang == 'es':
        flash(f"Habilidad '{skill_display}' eliminada de {player.name}.", "warning")
    else:
        flash(f"Skill '{skill.name}' removed from {player.name}.", "warning")
    
    return redirect(url_for("teams.edit_player", team_id=team.id, player_id=player.id))


@teams_bp.route("/<int:team_id>/purchase", methods=["POST"])
@login_required
def purchase(team_id: int):
    """Purchase team upgrades (rerolls, staff, etc.)."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    item = request.form.get("item")
    costs = {
        "reroll": team.race.reroll_cost,
        "assistant_coach": 10000,
        "cheerleader": 10000,
        "apothecary": 50000
    }
    
    if item not in costs:
        if str(get_locale()) == 'es':
            flash("Compra inválida.", "danger")
        else:
            flash("Invalid purchase.", "danger")
        return redirect(url_for("teams.view", team_id=team.id))
    
    cost = costs[item]
    
    if team.treasury < cost:
        if str(get_locale()) == 'es':
            flash("¡No hay suficiente oro en la tesorería!", "danger")
        else:
            flash("Not enough gold in treasury!", "danger")
        return redirect(url_for("teams.view", team_id=team.id))
    
    # Check limits
    if item == "apothecary":
        if team.has_apothecary:
            if str(get_locale()) == 'es':
                flash("El equipo ya tiene un boticario.", "warning")
            else:
                flash("Team already has an apothecary.", "warning")
            return redirect(url_for("teams.view", team_id=team.id))
        if not team.race.apothecary_allowed:
            if str(get_locale()) == 'es':
                flash("Esta raza no puede contratar un boticario.", "warning")
            else:
                flash("This race cannot hire an apothecary.", "warning")
            return redirect(url_for("teams.view", team_id=team.id))
        team.has_apothecary = True
    elif item == "reroll":
        team.rerolls += 1
    elif item == "assistant_coach":
        team.assistant_coaches += 1
    elif item == "cheerleader":
        team.cheerleaders += 1
    
    team.treasury -= cost
    team.calculate_tv()
    db.session.commit()
    
    if str(get_locale()) == 'es':
        flash(f"¡{item.replace('_', ' ').title()} comprado por {cost:,}g!", "success")
    else:
        flash(f"Purchased {item.replace('_', ' ')} for {cost:,}g!", "success")
    return redirect(url_for("teams.view", team_id=team.id))


@teams_bp.route("/<int:team_id>/star-players")
@login_required
def star_players(team_id: int):
    """View available star players to hire."""
    from app.models import StarPlayer
    
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Get star players available to this team's race
    available_stars = StarPlayer.query.filter(
        StarPlayer.available_to_races.any(id=team.race_id)
    ).order_by(StarPlayer.name).all()
    
    # Filter out already hired star players
    hired_ids = [sp.id for sp in team.star_players]
    available_stars = [sp for sp in available_stars if sp.id not in hired_ids]
    
    return render_template(
        "teams/star_players.html",
        team=team,
        available_stars=available_stars,
        hired_stars=team.star_players
    )


@teams_bp.route("/<int:team_id>/hire-star/<int:star_id>", methods=["POST"])
@login_required
def hire_star_player(team_id: int, star_id: int):
    """Hire a star player."""
    from app.models import StarPlayer
    from flask import session
    
    team = Team.query.get_or_404(team_id)
    star = StarPlayer.query.get_or_404(star_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    lang = session.get('language', 'en')
    
    # Check if star player is available to this race
    if team.race not in star.available_to_races:
        if lang == 'es':
            flash(f"{star.name} no está disponible para equipos {team.race.name}.", "danger")
        else:
            flash(f"{star.name} is not available for {team.race.name} teams.", "danger")
        return redirect(url_for("teams.star_players", team_id=team.id))
    
    # Check if already hired
    if star in team.star_players:
        if lang == 'es':
            flash(f"{star.name} ya está contratado.", "warning")
        else:
            flash(f"{star.name} is already hired.", "warning")
        return redirect(url_for("teams.star_players", team_id=team.id))
    
    # Check treasury
    if team.treasury < star.cost:
        if lang == 'es':
            flash(f"No hay suficiente oro en la tesorería. Necesitas {star.cost:,}g.", "danger")
        else:
            flash(f"Not enough gold in treasury. Need {star.cost:,}g.", "danger")
        return redirect(url_for("teams.star_players", team_id=team.id))
    
    # Hire star player
    team.star_players.append(star)
    team.treasury -= star.cost
    team.calculate_tv()
    db.session.commit()
    
    if lang == 'es':
        flash(f"¡{star.name} contratado por {star.cost:,}g!", "success")
    else:
        flash(f"{star.name} hired for {star.cost:,}g!", "success")
    return redirect(url_for("teams.star_players", team_id=team.id))


@teams_bp.route("/<int:team_id>/fire-star/<int:star_id>", methods=["POST"])
@login_required
def fire_star_player(team_id: int, star_id: int):
    """Release a star player."""
    from app.models import StarPlayer
    from flask import session
    
    team = Team.query.get_or_404(team_id)
    star = StarPlayer.query.get_or_404(star_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    lang = session.get('language', 'en')
    
    if star not in team.star_players:
        if lang == 'es':
            flash(f"{star.name} no está en este equipo.", "warning")
        else:
            flash(f"{star.name} is not on this team.", "warning")
        return redirect(url_for("teams.star_players", team_id=team.id))
    
    # Release star player (no refund in Blood Bowl)
    team.star_players.remove(star)
    team.calculate_tv()
    db.session.commit()
    
    if lang == 'es':
        flash(f"{star.name} ha sido liberado.", "warning")
    else:
        flash(f"{star.name} has been released.", "warning")
    return redirect(url_for("teams.star_players", team_id=team.id))

