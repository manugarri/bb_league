#!/usr/bin/env python
"""Team export and import utilities."""
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
    Team, Player, PlayerSkill, PlayerTrait, TeamStaff, TeamStarPlayer,
    Race, Position, Skill, Trait, StarPlayer, User
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


def export_teams(output_file: str):
    """Export all teams to a JSON file."""
    app = create_app()
    
    with app.app_context():
        teams = Team.query.all()
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "teams": []
        }
        
        for team in teams:
            print(f"Exporting team: {team.name}")
            
            # Get coach info
            coach = db.session.get(User, team.coach_id)
            
            # Export team data
            team_data = {
                "name": team.name,
                "coach_username": coach.username if coach else None,
                "race_name": team.race.name,
                "treasury": team.treasury,
                "rerolls": team.rerolls,
                "fan_factor": team.fan_factor,
                "assistant_coaches": team.assistant_coaches,
                "cheerleaders": team.cheerleaders,
                "has_apothecary": team.has_apothecary,
                "current_tv": team.current_tv,
                "games_played": team.games_played,
                "wins": team.wins,
                "draws": team.draws,
                "losses": team.losses,
                "touchdowns_for": team.touchdowns_for,
                "touchdowns_against": team.touchdowns_against,
                "casualties_inflicted": team.casualties_inflicted,
                "casualties_suffered": team.casualties_suffered,
                "is_active": team.is_active,
                "created_at": serialize_datetime(team.created_at),
                "updated_at": serialize_datetime(team.updated_at),
                "players": [],
                "staff": [],
                "star_players": []
            }
            
            # Export players
            for player in team.players.all():
                player_data = {
                    "name": player.name,
                    "number": player.number,
                    "position_name": player.position.name,
                    "movement": player.movement,
                    "strength": player.strength,
                    "agility": player.agility,
                    "passing": player.passing,
                    "armor": player.armor,
                    "spp": player.spp,
                    "level": player.level,
                    "games_played": player.games_played,
                    "touchdowns": player.touchdowns,
                    "casualties_inflicted": player.casualties_inflicted,
                    "completions": player.completions,
                    "interceptions": player.interceptions,
                    "deflections": player.deflections,
                    "mvp_awards": player.mvp_awards,
                    "is_active": player.is_active,
                    "is_dead": player.is_dead,
                    "miss_next_game": player.miss_next_game,
                    "niggling_injuries": player.niggling_injuries,
                    "value": player.value,
                    "hired_at": serialize_datetime(player.hired_at),
                    "skills": [],
                    "traits": []
                }
                
                # Export player skills
                for ps in player.skills.all():
                    player_data["skills"].append({
                        "skill_name": ps.skill.name,
                        "is_starting": ps.is_starting
                    })
                
                # Export player traits
                for pt in player.traits.all():
                    player_data["traits"].append({
                        "trait_name": pt.trait.name,
                        "is_starting": pt.is_starting
                    })
                
                team_data["players"].append(player_data)
            
            # Export staff
            for staff in team.staff.all():
                team_data["staff"].append({
                    "staff_type": staff.staff_type,
                    "name": staff.name,
                    "cost": staff.cost,
                    "hired_at": serialize_datetime(staff.hired_at)
                })
            
            # Export hired star players
            for star in team.star_players:
                team_data["star_players"].append({
                    "star_player_name": star.name
                })
            
            export_data["teams"].append(team_data)
            print(f"  Exported {len(team_data['players'])} players")
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nTeams exported to: {output_path}")
        print(f"Total teams: {len(export_data['teams'])}")


def import_teams(input_file: str, reset: bool = False):
    """Import teams from a JSON file."""
    app = create_app()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    print(f"Importing from: {input_path}")
    print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
    print(f"Mode: {'RESET (clearing existing teams)' if reset else 'ADD (adding to existing)'}")
    
    with app.app_context():
        if reset:
            print("\nClearing existing teams...")
            # Delete in reverse order to handle foreign keys
            PlayerSkill.query.delete()
            PlayerTrait.query.delete()
            TeamStaff.query.delete()
            TeamStarPlayer.query.delete()
            # Clear team_star_players association table
            db.session.execute(db.text("DELETE FROM team_star_players"))
            Player.query.delete()
            Team.query.delete()
            db.session.commit()
            print("Existing teams cleared.")
        
        imported_count = 0
        skipped_count = 0
        
        for team_data in import_data["teams"]:
            team_name = team_data["name"]
            
            # Check if team already exists
            existing_team = Team.query.filter_by(name=team_name).first()
            if existing_team and not reset:
                print(f"Skipping team '{team_name}' - already exists")
                skipped_count += 1
                continue
            
            # Find coach by username
            coach = User.query.filter_by(username=team_data["coach_username"]).first()
            if not coach:
                print(f"Warning: Coach '{team_data['coach_username']}' not found for team '{team_name}', skipping...")
                skipped_count += 1
                continue
            
            # Find race by name
            race = Race.query.filter_by(name=team_data["race_name"]).first()
            if not race:
                print(f"Warning: Race '{team_data['race_name']}' not found for team '{team_name}', skipping...")
                skipped_count += 1
                continue
            
            print(f"Importing team: {team_name}")
            
            # Create team
            team = Team(
                name=team_name,
                coach_id=coach.id,
                race_id=race.id,
                treasury=team_data.get("treasury", 1000000),
                rerolls=team_data.get("rerolls", 0),
                fan_factor=team_data.get("fan_factor", 1),
                assistant_coaches=team_data.get("assistant_coaches", 0),
                cheerleaders=team_data.get("cheerleaders", 0),
                has_apothecary=team_data.get("has_apothecary", False),
                current_tv=team_data.get("current_tv", 0),
                games_played=team_data.get("games_played", 0),
                wins=team_data.get("wins", 0),
                draws=team_data.get("draws", 0),
                losses=team_data.get("losses", 0),
                touchdowns_for=team_data.get("touchdowns_for", 0),
                touchdowns_against=team_data.get("touchdowns_against", 0),
                casualties_inflicted=team_data.get("casualties_inflicted", 0),
                casualties_suffered=team_data.get("casualties_suffered", 0),
                is_active=team_data.get("is_active", True),
                created_at=deserialize_datetime(team_data.get("created_at")) or datetime.utcnow(),
                updated_at=deserialize_datetime(team_data.get("updated_at")) or datetime.utcnow()
            )
            db.session.add(team)
            db.session.flush()  # Get team ID
            
            # Import players
            for player_data in team_data.get("players", []):
                # Find position by name and race
                position = Position.query.filter_by(
                    name=player_data["position_name"],
                    race_id=race.id
                ).first()
                
                if not position:
                    print(f"  Warning: Position '{player_data['position_name']}' not found, skipping player...")
                    continue
                
                player = Player(
                    team_id=team.id,
                    position_id=position.id,
                    name=player_data["name"],
                    number=player_data.get("number"),
                    movement=player_data.get("movement") or position.movement,
                    strength=player_data.get("strength") or position.strength,
                    agility=player_data.get("agility") or position.agility,
                    passing=player_data.get("passing") or position.passing,
                    armor=player_data.get("armor") or position.armor,
                    spp=player_data.get("spp", 0),
                    level=player_data.get("level", 1),
                    games_played=player_data.get("games_played", 0),
                    touchdowns=player_data.get("touchdowns", 0),
                    casualties_inflicted=player_data.get("casualties_inflicted", 0),
                    completions=player_data.get("completions", 0),
                    interceptions=player_data.get("interceptions", 0),
                    deflections=player_data.get("deflections", 0),
                    mvp_awards=player_data.get("mvp_awards", 0),
                    is_active=player_data.get("is_active", True),
                    is_dead=player_data.get("is_dead", False),
                    miss_next_game=player_data.get("miss_next_game", False),
                    niggling_injuries=player_data.get("niggling_injuries", 0),
                    value=player_data.get("value", 0),
                    hired_at=deserialize_datetime(player_data.get("hired_at")) or datetime.utcnow()
                )
                db.session.add(player)
                db.session.flush()  # Get player ID
                
                # Import player skills
                for skill_data in player_data.get("skills", []):
                    skill = Skill.query.filter_by(name=skill_data["skill_name"]).first()
                    if skill:
                        ps = PlayerSkill(
                            player_id=player.id,
                            skill_id=skill.id,
                            is_starting=skill_data.get("is_starting", False)
                        )
                        db.session.add(ps)
                
                # Import player traits
                for trait_data in player_data.get("traits", []):
                    trait = Trait.query.filter_by(name=trait_data["trait_name"]).first()
                    if trait:
                        pt = PlayerTrait(
                            player_id=player.id,
                            trait_id=trait.id,
                            is_starting=trait_data.get("is_starting", True)
                        )
                        db.session.add(pt)
            
            # Import staff
            for staff_data in team_data.get("staff", []):
                staff = TeamStaff(
                    team_id=team.id,
                    staff_type=staff_data["staff_type"],
                    name=staff_data.get("name"),
                    cost=staff_data.get("cost", 0),
                    hired_at=deserialize_datetime(staff_data.get("hired_at")) or datetime.utcnow()
                )
                db.session.add(staff)
            
            # Import star players
            for star_data in team_data.get("star_players", []):
                star = StarPlayer.query.filter_by(name=star_data["star_player_name"]).first()
                if star and star not in team.star_players:
                    team.star_players.append(star)
            
            imported_count += 1
            print(f"  Imported {len(team_data.get('players', []))} players")
        
        db.session.commit()
        
        print(f"\nImport complete.")
        print(f"Teams imported: {imported_count}")
        if skipped_count > 0:
            print(f"Teams skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="Team export/import utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export teams to JSON")
    export_parser.add_argument(
        "-o", "--output",
        default="backups/teams_export.json",
        help="Output file path (default: backups/teams_export.json)"
    )
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import teams from JSON")
    import_parser.add_argument(
        "-i", "--input",
        default="backups/teams_export.json",
        help="Input file path (default: backups/teams_export.json)"
    )
    import_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset (delete) all existing teams before import"
    )
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_teams(args.output)
    elif args.command == "import":
        import_teams(args.input, reset=args.reset)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

