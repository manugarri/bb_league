#!/usr/bin/env python
"""League export and import utilities."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import (
    League, Season, LeagueTeam, Standing, Match, MatchPlayerStats,
    User, Team, Player
)


def serialize_datetime(value):
    """Serialize datetime for JSON."""
    if value is None:
        return None
    return value.isoformat()


def deserialize_datetime(value):
    """Deserialize datetime from JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


def export_leagues(output_file: str):
    """Export all leagues to a JSON file."""
    app = create_app()
    
    with app.app_context():
        leagues = League.query.all()
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "leagues": []
        }
        
        for league in leagues:
            print(f"Exporting league: {league.name}")
            
            # Get commissioner info
            commissioner = db.session.get(User, league.commissioner_id)
            
            # Export league data
            league_data = {
                "name": league.name,
                "commissioner_username": commissioner.username if commissioner else None,
                "description": league.description,
                "format": league.format,
                "max_teams": league.max_teams,
                "min_teams": league.min_teams,
                "starting_treasury": league.starting_treasury,
                "max_team_value": league.max_team_value,
                "min_roster_size": league.min_roster_size,
                "max_roster_size": league.max_roster_size,
                "allow_star_players": league.allow_star_players,
                "win_points": league.win_points,
                "draw_points": league.draw_points,
                "loss_points": league.loss_points,
                "status": league.status,
                "registration_open": league.registration_open,
                "is_public": league.is_public,
                "house_rules": league.house_rules,
                "created_at": serialize_datetime(league.created_at),
                "updated_at": serialize_datetime(league.updated_at),
                "seasons": [],
                "league_teams": [],
                "matches": []
            }
            
            # Export seasons
            for season in league.seasons.all():
                season_data = {
                    "name": season.name,
                    "number": season.number,
                    "start_date": serialize_datetime(season.start_date),
                    "end_date": serialize_datetime(season.end_date),
                    "is_active": season.is_active,
                    "is_completed": season.is_completed,
                    "current_round": season.current_round,
                    "total_rounds": season.total_rounds,
                    "created_at": serialize_datetime(season.created_at),
                    "standings": []
                }
                
                # Export standings for this season
                for standing in season.standings.all():
                    standing_data = {
                        "team_name": standing.team.name if standing.team else None,
                        "rank": standing.rank,
                        "played": standing.played,
                        "wins": standing.wins,
                        "draws": standing.draws,
                        "losses": standing.losses,
                        "points": standing.points,
                        "bonus_points": standing.bonus_points,
                        "bonus_high_scoring": standing.bonus_high_scoring,
                        "bonus_opponent_high_scoring": standing.bonus_opponent_high_scoring,
                        "bonus_casualties": standing.bonus_casualties,
                        "touchdowns_for": standing.touchdowns_for,
                        "touchdowns_against": standing.touchdowns_against,
                        "casualties_inflicted": standing.casualties_inflicted,
                        "casualties_suffered": standing.casualties_suffered
                    }
                    season_data["standings"].append(standing_data)
                
                league_data["seasons"].append(season_data)
            
            # Export league team registrations
            for lt in league.teams.all():
                lt_data = {
                    "team_name": lt.team.name if lt.team else None,
                    "is_approved": lt.is_approved,
                    "approved_at": serialize_datetime(lt.approved_at),
                    "seed": lt.seed,
                    "registered_at": serialize_datetime(lt.registered_at)
                }
                league_data["league_teams"].append(lt_data)
            
            # Export matches
            for match in league.matches.all():
                match_data = {
                    "season_name": match.season.name if match.season else None,
                    "home_team_name": match.home_team.name if match.home_team else None,
                    "away_team_name": match.away_team.name if match.away_team else None,
                    "round_number": match.round_number,
                    "scheduled_date": serialize_datetime(match.scheduled_date),
                    "played_date": serialize_datetime(match.played_date),
                    "home_score": match.home_score,
                    "away_score": match.away_score,
                    "home_casualties": match.home_casualties,
                    "away_casualties": match.away_casualties,
                    "home_winnings": match.home_winnings,
                    "away_winnings": match.away_winnings,
                    "home_fan_factor_change": match.home_fan_factor_change,
                    "away_fan_factor_change": match.away_fan_factor_change,
                    "status": match.status,
                    "is_validated": match.is_validated,
                    "validator_username": match.validator.username if match.validator else None,
                    "validated_at": serialize_datetime(match.validated_at),
                    "notes": match.notes,
                    "created_at": serialize_datetime(match.created_at),
                    "updated_at": serialize_datetime(match.updated_at),
                    "player_stats": []
                }
                
                # Export player stats for this match
                for ps in match.player_stats.all():
                    ps_data = {
                        "player_name": ps.player.name if ps.player else None,
                        "team_name": ps.team.name if ps.team else None,
                        "touchdowns": ps.touchdowns,
                        "completions": ps.completions,
                        "passing_yards": ps.passing_yards,
                        "rushing_yards": ps.rushing_yards,
                        "receiving_yards": ps.receiving_yards,
                        "interceptions": ps.interceptions,
                        "deflections": ps.deflections,
                        "casualties_inflicted": ps.casualties_inflicted,
                        "casualties_suffered": ps.casualties_suffered,
                        "is_mvp": ps.is_mvp,
                        "injury_result": ps.injury_result,
                        "was_killed": ps.was_killed,
                        "spp_earned": ps.spp_earned
                    }
                    match_data["player_stats"].append(ps_data)
                
                league_data["matches"].append(match_data)
            
            export_data["leagues"].append(league_data)
            print(f"  Exported {len(league_data['seasons'])} seasons, {len(league_data['league_teams'])} teams, {len(league_data['matches'])} matches")
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nLeagues exported to: {output_path}")
        print(f"Total leagues: {len(export_data['leagues'])}")


def import_leagues(input_file: str, reset: bool = False):
    """Import leagues from a JSON file."""
    app = create_app()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    print(f"Importing from: {input_path}")
    print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
    print(f"Mode: {'RESET (clearing existing leagues)' if reset else 'ADD (adding to existing)'}")
    
    with app.app_context():
        if reset:
            print("\nClearing existing leagues...")
            # Delete in reverse order to handle foreign keys
            MatchPlayerStats.query.delete()
            Match.query.delete()
            Standing.query.delete()
            LeagueTeam.query.delete()
            Season.query.delete()
            League.query.delete()
            db.session.commit()
            print("Existing leagues cleared.")
        
        imported_count = 0
        skipped_count = 0
        
        for league_data in import_data["leagues"]:
            league_name = league_data["name"]
            
            # Check if league already exists
            existing_league = League.query.filter_by(name=league_name).first()
            if existing_league and not reset:
                print(f"Skipping league '{league_name}' - already exists")
                skipped_count += 1
                continue
            
            # Find commissioner by username
            commissioner = User.query.filter_by(username=league_data["commissioner_username"]).first()
            if not commissioner:
                print(f"Warning: Commissioner '{league_data['commissioner_username']}' not found for league '{league_name}', skipping...")
                skipped_count += 1
                continue
            
            print(f"Importing league: {league_name}")
            
            # Create league
            league = League(
                name=league_name,
                commissioner_id=commissioner.id,
                description=league_data.get("description"),
                format=league_data.get("format", "round_robin"),
                max_teams=league_data.get("max_teams", 8),
                min_teams=league_data.get("min_teams", 4),
                starting_treasury=league_data.get("starting_treasury", 1000000),
                max_team_value=league_data.get("max_team_value"),
                min_roster_size=league_data.get("min_roster_size", 11),
                max_roster_size=league_data.get("max_roster_size", 16),
                allow_star_players=league_data.get("allow_star_players", True),
                win_points=league_data.get("win_points", 3),
                draw_points=league_data.get("draw_points", 1),
                loss_points=league_data.get("loss_points", 0),
                status=league_data.get("status", "registration"),
                registration_open=league_data.get("registration_open", True),
                is_public=league_data.get("is_public", True),
                house_rules=league_data.get("house_rules"),
                created_at=deserialize_datetime(league_data.get("created_at")) or datetime.utcnow(),
                updated_at=deserialize_datetime(league_data.get("updated_at")) or datetime.utcnow()
            )
            db.session.add(league)
            db.session.flush()  # Get league ID
            
            # Create a mapping of season names to season objects
            season_map = {}
            
            # Import seasons
            for season_data in league_data.get("seasons", []):
                season = Season(
                    league_id=league.id,
                    name=season_data["name"],
                    number=season_data.get("number", 1),
                    start_date=deserialize_datetime(season_data.get("start_date")),
                    end_date=deserialize_datetime(season_data.get("end_date")),
                    is_active=season_data.get("is_active", True),
                    is_completed=season_data.get("is_completed", False),
                    current_round=season_data.get("current_round", 1),
                    total_rounds=season_data.get("total_rounds"),
                    created_at=deserialize_datetime(season_data.get("created_at")) or datetime.utcnow()
                )
                db.session.add(season)
                db.session.flush()
                season_map[season_data["name"]] = season
                
                # Import standings for this season
                for standing_data in season_data.get("standings", []):
                    team = Team.query.filter_by(name=standing_data["team_name"]).first()
                    if not team:
                        print(f"  Warning: Team '{standing_data['team_name']}' not found for standing, skipping...")
                        continue
                    
                    standing = Standing(
                        season_id=season.id,
                        team_id=team.id,
                        rank=standing_data.get("rank"),
                        played=standing_data.get("played", 0),
                        wins=standing_data.get("wins", 0),
                        draws=standing_data.get("draws", 0),
                        losses=standing_data.get("losses", 0),
                        points=standing_data.get("points", 0),
                        bonus_points=standing_data.get("bonus_points", 0),
                        bonus_high_scoring=standing_data.get("bonus_high_scoring", 0),
                        bonus_opponent_high_scoring=standing_data.get("bonus_opponent_high_scoring", 0),
                        bonus_casualties=standing_data.get("bonus_casualties", 0),
                        touchdowns_for=standing_data.get("touchdowns_for", 0),
                        touchdowns_against=standing_data.get("touchdowns_against", 0),
                        casualties_inflicted=standing_data.get("casualties_inflicted", 0),
                        casualties_suffered=standing_data.get("casualties_suffered", 0)
                    )
                    db.session.add(standing)
            
            # Import league team registrations
            for lt_data in league_data.get("league_teams", []):
                team = Team.query.filter_by(name=lt_data["team_name"]).first()
                if not team:
                    print(f"  Warning: Team '{lt_data['team_name']}' not found for registration, skipping...")
                    continue
                
                league_team = LeagueTeam(
                    league_id=league.id,
                    team_id=team.id,
                    is_approved=lt_data.get("is_approved", False),
                    approved_at=deserialize_datetime(lt_data.get("approved_at")),
                    seed=lt_data.get("seed"),
                    registered_at=deserialize_datetime(lt_data.get("registered_at")) or datetime.utcnow()
                )
                db.session.add(league_team)
            
            # Import matches
            for match_data in league_data.get("matches", []):
                home_team = Team.query.filter_by(name=match_data["home_team_name"]).first()
                away_team = Team.query.filter_by(name=match_data["away_team_name"]).first()
                
                if not home_team or not away_team:
                    print(f"  Warning: Teams not found for match, skipping...")
                    continue
                
                # Get season
                season = season_map.get(match_data.get("season_name"))
                
                # Get validator
                validator = None
                if match_data.get("validator_username"):
                    validator = User.query.filter_by(username=match_data["validator_username"]).first()
                
                match = Match(
                    league_id=league.id,
                    season_id=season.id if season else None,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    round_number=match_data.get("round_number"),
                    scheduled_date=deserialize_datetime(match_data.get("scheduled_date")),
                    played_date=deserialize_datetime(match_data.get("played_date")),
                    home_score=match_data.get("home_score", 0),
                    away_score=match_data.get("away_score", 0),
                    home_casualties=match_data.get("home_casualties", 0),
                    away_casualties=match_data.get("away_casualties", 0),
                    home_winnings=match_data.get("home_winnings", 0),
                    away_winnings=match_data.get("away_winnings", 0),
                    home_fan_factor_change=match_data.get("home_fan_factor_change", 0),
                    away_fan_factor_change=match_data.get("away_fan_factor_change", 0),
                    status=match_data.get("status", "scheduled"),
                    is_validated=match_data.get("is_validated", False),
                    validated_by=validator.id if validator else None,
                    validated_at=deserialize_datetime(match_data.get("validated_at")),
                    notes=match_data.get("notes"),
                    created_at=deserialize_datetime(match_data.get("created_at")) or datetime.utcnow(),
                    updated_at=deserialize_datetime(match_data.get("updated_at")) or datetime.utcnow()
                )
                db.session.add(match)
                db.session.flush()
                
                # Import player stats for this match
                for ps_data in match_data.get("player_stats", []):
                    # Find player by name and team
                    team = Team.query.filter_by(name=ps_data["team_name"]).first()
                    player = None
                    if team:
                        player = Player.query.filter_by(
                            team_id=team.id,
                            name=ps_data["player_name"]
                        ).first()
                    
                    if not player or not team:
                        continue
                    
                    player_stats = MatchPlayerStats(
                        match_id=match.id,
                        player_id=player.id,
                        team_id=team.id,
                        touchdowns=ps_data.get("touchdowns", 0),
                        completions=ps_data.get("completions", 0),
                        passing_yards=ps_data.get("passing_yards", 0),
                        rushing_yards=ps_data.get("rushing_yards", 0),
                        receiving_yards=ps_data.get("receiving_yards", 0),
                        interceptions=ps_data.get("interceptions", 0),
                        deflections=ps_data.get("deflections", 0),
                        casualties_inflicted=ps_data.get("casualties_inflicted", 0),
                        casualties_suffered=ps_data.get("casualties_suffered", 0),
                        is_mvp=ps_data.get("is_mvp", False),
                        injury_result=ps_data.get("injury_result"),
                        was_killed=ps_data.get("was_killed", False),
                        spp_earned=ps_data.get("spp_earned", 0)
                    )
                    db.session.add(player_stats)
            
            imported_count += 1
            print(f"  Imported {len(league_data.get('seasons', []))} seasons, {len(league_data.get('league_teams', []))} teams, {len(league_data.get('matches', []))} matches")
        
        db.session.commit()
        
        print(f"\nImport complete.")
        print(f"Leagues imported: {imported_count}")
        if skipped_count > 0:
            print(f"Leagues skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="League export/import utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export leagues to JSON")
    export_parser.add_argument(
        "-o", "--output",
        default="backups/leagues_export.json",
        help="Output file path (default: backups/leagues_export.json)"
    )
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import leagues from JSON")
    import_parser.add_argument(
        "-i", "--input",
        default="backups/leagues_export.json",
        help="Input file path (default: backups/leagues_export.json)"
    )
    import_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset (delete) all existing leagues before import"
    )
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_leagues(args.output)
    elif args.command == "import":
        import_leagues(args.input, reset=args.reset)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

