"""Matches API routes."""
from flask import jsonify, request
from app.blueprints.api import api_bp
from app.models import Match


@api_bp.route("/matches")
def get_matches():
    """Get all matches."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    league_id = request.args.get("league_id", type=int)
    
    query = Match.query
    
    if status:
        query = query.filter_by(status=status)
    
    if league_id:
        query = query.filter_by(league_id=league_id)
    
    matches = query.order_by(Match.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        "matches": [{
            "id": m.id,
            "home_team": {
                "id": m.home_team.id,
                "name": m.home_team.name
            },
            "away_team": {
                "id": m.away_team.id,
                "name": m.away_team.name
            },
            "score": m.get_score_string() if m.is_completed else None,
            "status": m.status,
            "round": m.round_number,
            "league": m.league.name if m.league else None
        } for m in matches.items],
        "total": matches.total,
        "pages": matches.pages,
        "current_page": matches.page
    })


@api_bp.route("/matches/<int:match_id>")
def get_match(match_id: int):
    """Get match details."""
    match = Match.query.get_or_404(match_id)
    
    # Get player stats
    home_stats = [{
        "player": {
            "id": s.player.id,
            "name": s.player.name,
            "position": s.player.position.name
        },
        "touchdowns": s.touchdowns,
        "completions": s.completions,
        "interceptions": s.interceptions,
        "casualties": s.casualties_inflicted,
        "mvp": s.is_mvp,
        "spp": s.spp_earned
    } for s in match.player_stats.filter_by(team_id=match.home_team_id).all()]
    
    away_stats = [{
        "player": {
            "id": s.player.id,
            "name": s.player.name,
            "position": s.player.position.name
        },
        "touchdowns": s.touchdowns,
        "completions": s.completions,
        "interceptions": s.interceptions,
        "casualties": s.casualties_inflicted,
        "mvp": s.is_mvp,
        "spp": s.spp_earned
    } for s in match.player_stats.filter_by(team_id=match.away_team_id).all()]
    
    return jsonify({
        "id": match.id,
        "home_team": {
            "id": match.home_team.id,
            "name": match.home_team.name,
            "score": match.home_score,
            "casualties": match.home_casualties,
            "winnings": match.home_winnings,
            "player_stats": home_stats
        },
        "away_team": {
            "id": match.away_team.id,
            "name": match.away_team.name,
            "score": match.away_score,
            "casualties": match.away_casualties,
            "winnings": match.away_winnings,
            "player_stats": away_stats
        },
        "status": match.status,
        "round": match.round_number,
        "league": {
            "id": match.league.id,
            "name": match.league.name
        } if match.league else None,
        "played_date": match.played_date.isoformat() if match.played_date else None,
        "notes": match.notes
    })

