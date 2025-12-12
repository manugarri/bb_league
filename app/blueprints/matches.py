"""Matches blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Match, MatchPlayerStats, Player, Standing, Team
from app.forms.match import RecordMatchForm, MatchPlayerStatsForm

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/")
@login_required
def index():
    """List all matches."""
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    
    query = Match.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    matches = query.order_by(Match.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template(
        "matches/index.html",
        matches=matches,
        current_status=status_filter
    )


@matches_bp.route("/<int:match_id>")
@login_required
def view(match_id: int):
    """View match details."""
    match = Match.query.get_or_404(match_id)
    
    # Get player stats grouped by team
    home_stats = match.player_stats.filter_by(team_id=match.home_team_id).all()
    away_stats = match.player_stats.filter_by(team_id=match.away_team_id).all()
    
    # Check if current user can record result
    can_record = False
    if current_user.is_authenticated and match.status == "scheduled":
        is_home_coach = current_user.id == match.home_team.coach_id
        is_away_coach = current_user.id == match.away_team.coach_id
        is_commissioner = match.league and current_user.id == match.league.commissioner_id
        can_record = is_home_coach or is_away_coach or is_commissioner
    
    return render_template(
        "matches/view.html",
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        can_record=can_record
    )


@matches_bp.route("/<int:match_id>/record", methods=["GET", "POST"])
@login_required
def record(match_id: int):
    """Record match result."""
    match = Match.query.get_or_404(match_id)
    
    # Check permission
    is_home_coach = current_user.id == match.home_team.coach_id
    is_away_coach = current_user.id == match.away_team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_home_coach or is_away_coach or is_commissioner or current_user.is_admin):
        abort(403)
    
    # Only admins can edit completed matches
    if match.status == "completed" and not current_user.is_admin:
        flash("This match has already been recorded.", "warning")
        return redirect(url_for("matches.view", match_id=match.id))
    
    form = RecordMatchForm()
    
    # Get players for both teams
    home_players = match.home_team.players.filter_by(is_active=True).all()
    away_players = match.away_team.players.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        # Update match score
        match.home_score = form.home_score.data
        match.away_score = form.away_score.data
        match.home_casualties = form.home_casualties.data
        match.away_casualties = form.away_casualties.data
        match.home_winnings = form.home_winnings.data
        match.away_winnings = form.away_winnings.data
        match.notes = form.notes.data
        match.status = "completed"
        match.played_date = datetime.utcnow()
        
        # Update team treasuries
        match.home_team.treasury += form.home_winnings.data
        match.away_team.treasury += form.away_winnings.data
        
        # Update team stats
        update_team_stats(match)
        
        # Update standings
        if match.league and match.league.current_season:
            update_standings(match)
        
        db.session.commit()
        
        flash("Match result recorded successfully!", "success")
        return redirect(url_for("matches.player_stats", match_id=match.id))
    
    return render_template(
        "matches/record.html",
        form=form,
        match=match,
        home_players=home_players,
        away_players=away_players
    )


@matches_bp.route("/<int:match_id>/player-stats", methods=["GET", "POST"])
@login_required
def player_stats(match_id: int):
    """Record individual player statistics."""
    match = Match.query.get_or_404(match_id)
    
    # Check permission
    is_home_coach = current_user.id == match.home_team.coach_id
    is_away_coach = current_user.id == match.away_team.coach_id
    is_commissioner = match.league and current_user.id == match.league.commissioner_id
    
    if not (is_home_coach or is_away_coach or is_commissioner or current_user.is_admin):
        abort(403)
    
    home_players = match.home_team.players.filter_by(is_active=True).all()
    away_players = match.away_team.players.filter_by(is_active=True).all()
    
    if request.method == "POST":
        # Process player stats from form
        for player in home_players + away_players:
            prefix = f"player_{player.id}_"
            
            # Get or create stats record
            stats = MatchPlayerStats.query.filter_by(
                match_id=match.id,
                player_id=player.id
            ).first()
            
            if not stats:
                stats = MatchPlayerStats(
                    match_id=match.id,
                    player_id=player.id,
                    team_id=player.team_id
                )
                db.session.add(stats)
            
            # Update stats
            stats.touchdowns = int(request.form.get(f"{prefix}touchdowns", 0) or 0)
            stats.completions = int(request.form.get(f"{prefix}completions", 0) or 0)
            stats.interceptions = int(request.form.get(f"{prefix}interceptions", 0) or 0)
            stats.casualties_inflicted = int(request.form.get(f"{prefix}casualties", 0) or 0)
            stats.is_mvp = request.form.get(f"{prefix}mvp") == "on"
            stats.injury_result = request.form.get(f"{prefix}injury") or None
            
            # Calculate SPP
            stats.calculate_spp()
            
            # Update player career stats
            player.touchdowns += stats.touchdowns
            player.completions += stats.completions
            player.interceptions += stats.interceptions
            player.casualties_inflicted += stats.casualties_inflicted
            if stats.is_mvp:
                player.mvp_awards += 1
            player.games_played += 1
            
            # Add SPP to player
            player.add_spp(stats.spp_earned)
            
            # Handle injuries
            if stats.injury_result:
                apply_injury(player, stats.injury_result, match.id)
        
        db.session.commit()
        
        # Update team values
        match.home_team.calculate_tv()
        match.away_team.calculate_tv()
        db.session.commit()
        
        flash("Player statistics recorded!", "success")
        return redirect(url_for("matches.view", match_id=match.id))
    
    # Get existing stats
    existing_stats = {
        s.player_id: s for s in match.player_stats.all()
    }
    
    return render_template(
        "matches/player_stats.html",
        match=match,
        home_players=home_players,
        away_players=away_players,
        existing_stats=existing_stats
    )


def update_team_stats(match: Match) -> None:
    """Update team statistics from match result."""
    home = match.home_team
    away = match.away_team
    
    home.games_played += 1
    away.games_played += 1
    
    home.touchdowns_for += match.home_score
    home.touchdowns_against += match.away_score
    away.touchdowns_for += match.away_score
    away.touchdowns_against += match.home_score
    
    home.casualties_inflicted += match.home_casualties
    home.casualties_suffered += match.away_casualties
    away.casualties_inflicted += match.away_casualties
    away.casualties_suffered += match.home_casualties
    
    if match.home_score > match.away_score:
        home.wins += 1
        away.losses += 1
    elif match.away_score > match.home_score:
        away.wins += 1
        home.losses += 1
    else:
        home.draws += 1
        away.draws += 1


def update_standings(match: Match) -> None:
    """Update league standings from match result."""
    season = match.league.current_season
    if not season:
        return
    
    # Get or create standings
    home_standing = Standing.query.filter_by(
        season_id=season.id,
        team_id=match.home_team_id
    ).first()
    
    away_standing = Standing.query.filter_by(
        season_id=season.id,
        team_id=match.away_team_id
    ).first()
    
    if home_standing:
        home_standing.update_from_match(True, match)
    
    if away_standing:
        away_standing.update_from_match(False, match)


def apply_injury(player: Player, injury_type: str, match_id: int) -> None:
    """Apply injury effect to player."""
    from app.models import Injury
    
    if injury_type == "badly_hurt":
        # No lasting effect
        pass
    elif injury_type == "miss_next_game":
        player.miss_next_game = True
    elif injury_type == "niggling":
        player.niggling_injuries += 1
    elif injury_type == "-1ma":
        player.movement = max(1, player.movement - 1)
    elif injury_type == "-1av":
        player.armor = max(1, player.armor - 1)
    elif injury_type == "-1ag":
        player.agility = max(1, player.agility - 1)
    elif injury_type == "-1st":
        player.strength = max(1, player.strength - 1)
    elif injury_type == "-1pa":
        player.passing = max(1, player.passing - 1) if player.passing else None
    elif injury_type == "dead":
        player.is_active = False
        player.is_dead = True
    
    # Record injury
    if injury_type and injury_type != "badly_hurt":
        injury = Injury(
            player_id=player.id,
            match_id=match_id,
            injury_type=injury_type,
            is_permanent=injury_type not in ["badly_hurt", "miss_next_game"]
        )
        db.session.add(injury)

