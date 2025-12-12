"""Teams blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Team, Race, Position, Player
from app.forms.team import CreateTeamForm, HirePlayerForm, EditTeamForm, EditPlayerForm

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/")
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
    form.race_id.choices = [(r.id, r.name) for r in Race.query.order_by(Race.name).all()]
    
    if form.validate_on_submit():
        team = Team(
            name=form.name.data,
            coach_id=current_user.id,
            race_id=form.race_id.data,
            treasury=1000000
        )
        db.session.add(team)
        db.session.commit()
        
        flash(f"Team '{team.name}' created successfully!", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    races = Race.query.order_by(Race.name).all()
    return render_template("teams/create.html", form=form, races=races)


@teams_bp.route("/<int:team_id>")
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
    
    return render_template(
        "teams/view.html",
        team=team,
        players=players,
        positions=available_positions,
        position_counts=position_counts,
        is_owner=current_user.is_authenticated and current_user.id == team.coach_id
    )


@teams_bp.route("/<int:team_id>/edit", methods=["GET", "POST"])
@login_required
def edit(team_id: int):
    """Edit team details."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    form = EditTeamForm(obj=team)
    
    if form.validate_on_submit():
        team.name = form.name.data
        db.session.commit()
        flash("Team updated successfully.", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    return render_template("teams/edit.html", form=form, team=team)


@teams_bp.route("/<int:team_id>/hire", methods=["GET", "POST"])
@login_required
def hire_player(team_id: int):
    """Hire a new player."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id:
        abort(403)
    
    form = HirePlayerForm()
    positions = Position.query.filter_by(race_id=team.race_id).order_by(Position.name).all()
    form.position_id.choices = [(p.id, f"{p.name} ({p.cost:,}g)") for p in positions]
    
    if form.validate_on_submit():
        position = Position.query.get(form.position_id.data)
        
        # Check treasury
        if team.treasury < position.cost:
            flash("Not enough gold in treasury!", "danger")
            return render_template("teams/hire_player.html", form=form, team=team)
        
        # Check roster limit
        if team.roster_count >= 16:
            flash("Roster is full! Maximum 16 players.", "danger")
            return render_template("teams/hire_player.html", form=form, team=team)
        
        # Check position limit
        current_count = team.players.filter_by(position_id=position.id, is_active=True).count()
        if current_count >= position.max_count:
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
        
        flash(f"Player '{player.name}' hired successfully!", "success")
        return redirect(url_for("teams.view", team_id=team.id))
    
    return render_template("teams/hire_player.html", form=form, team=team, positions=positions)


@teams_bp.route("/<int:team_id>/player/<int:player_id>")
def view_player(team_id: int, player_id: int):
    """View player details."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    
    if player.team_id != team.id:
        abort(404)
    
    # Get match history
    match_stats = player.match_stats.order_by(player.match_stats.c.id.desc()).limit(10).all() if hasattr(player.match_stats, 'c') else player.match_stats.limit(10).all()
    
    return render_template(
        "teams/player.html",
        team=team,
        player=player,
        match_stats=match_stats,
        is_owner=current_user.is_authenticated and current_user.id == team.coach_id
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
        flash("Player updated successfully.", "success")
        return redirect(url_for("teams.view_player", team_id=team.id, player_id=player.id))
    
    return render_template("teams/edit_player.html", form=form, team=team, player=player)


@teams_bp.route("/<int:team_id>/player/<int:player_id>/fire", methods=["POST"])
@login_required
def fire_player(team_id: int, player_id: int):
    """Fire (release) a player."""
    team = Team.query.get_or_404(team_id)
    player = Player.query.get_or_404(player_id)
    
    if player.team_id != team.id:
        abort(404)
    
    if team.coach_id != current_user.id:
        abort(403)
    
    player.is_active = False
    db.session.commit()
    
    team.calculate_tv()
    db.session.commit()
    
    flash(f"Player '{player.name}' has been released.", "warning")
    return redirect(url_for("teams.view", team_id=team.id))


@teams_bp.route("/<int:team_id>/purchase", methods=["POST"])
@login_required
def purchase(team_id: int):
    """Purchase team upgrades (rerolls, staff, etc.)."""
    team = Team.query.get_or_404(team_id)
    
    if team.coach_id != current_user.id:
        abort(403)
    
    item = request.form.get("item")
    costs = {
        "reroll": team.race.reroll_cost,
        "assistant_coach": 10000,
        "cheerleader": 10000,
        "apothecary": 50000
    }
    
    if item not in costs:
        flash("Invalid purchase.", "danger")
        return redirect(url_for("teams.view", team_id=team.id))
    
    cost = costs[item]
    
    if team.treasury < cost:
        flash("Not enough gold in treasury!", "danger")
        return redirect(url_for("teams.view", team_id=team.id))
    
    # Check limits
    if item == "apothecary":
        if team.has_apothecary:
            flash("Team already has an apothecary.", "warning")
            return redirect(url_for("teams.view", team_id=team.id))
        if not team.race.apothecary_allowed:
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
    
    flash(f"Purchased {item.replace('_', ' ')} for {cost:,}g!", "success")
    return redirect(url_for("teams.view", team_id=team.id))

