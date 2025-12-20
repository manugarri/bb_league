"""Leagues API routes."""
from flask import jsonify, request
from app.blueprints.api import api_bp
from app.models import League, Standing


@api_bp.route("/leagues")
def get_leagues():
    """Get all leagues."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    
    query = League.query.filter_by(is_public=True)
    
    if status:
        query = query.filter_by(status=status)
    
    leagues = query.order_by(League.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        "leagues": [{
            "id": l.id,
            "name": l.name,
            "commissioner": l.commissioner.username,
            "format": l.format,
            "status": l.status,
            "team_count": l.team_count,
            "max_teams": l.max_teams
        } for l in leagues.items],
        "total": leagues.total,
        "pages": leagues.pages,
        "current_page": leagues.page
    })


@api_bp.route("/leagues/<int:league_id>")
def get_league(league_id: int):
    """Get league details."""
    league = League.query.get_or_404(league_id)
    
    # Get standings
    standings = []
    if league.current_season:
        standings_query = Standing.query.filter_by(
            season_id=league.current_season.id
        ).order_by(Standing.points.desc()).all()
        
        standings = [{
            "rank": i + 1,
            "team": {
                "id": s.team.id,
                "name": s.team.name
            },
            "played": s.played,
            "wins": s.wins,
            "draws": s.draws,
            "losses": s.losses,
            "points": s.points,
            "bonus_points": s.bonus_points or 0,
            "td_diff": s.touchdown_diff
        } for i, s in enumerate(standings_query)]
    
    return jsonify({
        "id": league.id,
        "name": league.name,
        "description": league.description,
        "commissioner": {
            "id": league.commissioner.id,
            "username": league.commissioner.username
        },
        "format": league.format,
        "status": league.status,
        "team_count": league.team_count,
        "max_teams": league.max_teams,
        "scoring": {
            "win": league.win_points,
            "draw": league.draw_points,
            "loss": league.loss_points
        },
        "standings": standings
    })


@api_bp.route("/leagues/<int:league_id>/standings")
def get_league_standings(league_id: int):
    """Get league standings."""
    league = League.query.get_or_404(league_id)
    
    if not league.current_season:
        return jsonify({"standings": []})
    
    standings = Standing.query.filter_by(
        season_id=league.current_season.id
    ).order_by(Standing.points.desc(), Standing.touchdowns_for.desc()).all()
    
    return jsonify({
        "standings": [{
            "rank": i + 1,
            "team": {
                "id": s.team.id,
                "name": s.team.name,
                "race": s.team.race.name
            },
            "played": s.played,
            "wins": s.wins,
            "draws": s.draws,
            "losses": s.losses,
            "points": s.points,
            "bonus_points": s.bonus_points or 0,
            "bonus_breakdown": {
                "high_scoring": s.bonus_high_scoring or 0,
                "opponent_high_scoring": s.bonus_opponent_high_scoring or 0,
                "casualties": s.bonus_casualties or 0
            },
            "touchdowns_for": s.touchdowns_for,
            "touchdowns_against": s.touchdowns_against,
            "td_diff": s.touchdown_diff,
            "casualties": s.casualties_inflicted
        } for i, s in enumerate(standings)]
    })

