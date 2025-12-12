"""Teams API routes."""
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.blueprints.api import api_bp
from app.models import Team, Race, Position
from app.extensions import db


@api_bp.route("/teams")
def get_teams():
    """Get all teams."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    race_id = request.args.get("race_id", type=int)
    
    query = Team.query.filter_by(is_active=True)
    
    if race_id:
        query = query.filter_by(race_id=race_id)
    
    teams = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        "teams": [{
            "id": t.id,
            "name": t.name,
            "race": t.race.name,
            "coach": t.coach.username,
            "tv": t.current_tv,
            "record": t.get_record_string()
        } for t in teams.items],
        "total": teams.total,
        "pages": teams.pages,
        "current_page": teams.page
    })


@api_bp.route("/teams/<int:team_id>")
def get_team(team_id: int):
    """Get team details."""
    team = Team.query.get_or_404(team_id)
    
    return jsonify({
        "id": team.id,
        "name": team.name,
        "race": {
            "id": team.race.id,
            "name": team.race.name
        },
        "coach": {
            "id": team.coach.id,
            "username": team.coach.username
        },
        "treasury": team.treasury,
        "tv": team.current_tv,
        "rerolls": team.rerolls,
        "fan_factor": team.fan_factor,
        "assistant_coaches": team.assistant_coaches,
        "cheerleaders": team.cheerleaders,
        "has_apothecary": team.has_apothecary,
        "stats": {
            "games_played": team.games_played,
            "wins": team.wins,
            "draws": team.draws,
            "losses": team.losses,
            "touchdowns_for": team.touchdowns_for,
            "touchdowns_against": team.touchdowns_against,
            "casualties_inflicted": team.casualties_inflicted
        },
        "players": [{
            "id": p.id,
            "name": p.name,
            "number": p.number,
            "position": p.position.name,
            "spp": p.spp,
            "is_active": p.is_active
        } for p in team.players.all()]
    })


@api_bp.route("/races")
def get_races():
    """Get all available races."""
    races = Race.query.order_by(Race.name).all()
    
    return jsonify({
        "races": [{
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "reroll_cost": r.reroll_cost,
            "apothecary_allowed": r.apothecary_allowed,
            "tier": r.tier
        } for r in races]
    })


@api_bp.route("/races/<int:race_id>/positions")
def get_positions(race_id: int):
    """Get positions for a race."""
    race = Race.query.get_or_404(race_id)
    positions = Position.query.filter_by(race_id=race_id).order_by(Position.name).all()
    
    return jsonify({
        "race": race.name,
        "positions": [{
            "id": p.id,
            "name": p.name,
            "cost": p.cost,
            "max_count": p.max_count,
            "stats": {
                "ma": p.movement,
                "st": p.strength,
                "ag": p.agility,
                "pa": p.passing,
                "av": p.armor
            }
        } for p in positions]
    })

