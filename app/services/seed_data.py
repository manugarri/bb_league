"""Seed data for Blood Bowl races, positions, skills, and star players."""
import json
import os
from app.extensions import db
from app.models import Race, Position, Skill, Trait, StarPlayer


def get_data_path(filename: str) -> str:
    """Get the path to a data file."""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "data", filename)


def seed_skills_and_traits():
    """Seed Blood Bowl skills and traits from JSON data."""
    json_path = get_data_path("skills.json")
    
    if not os.path.exists(json_path):
        print(f"  Warning: skills.json not found at {json_path}")
        return 0, 0
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    skill_count = 0
    trait_count = 0
    
    # Seed skills
    for skill_data in data.get("skills", []):
        existing = Skill.query.filter_by(name=skill_data["name"]).first()
        if not existing:
            skill = Skill(
                name=skill_data["name"],
                name_es=skill_data.get("name_es"),
                category=skill_data.get("category", "G"),
                skill_type=skill_data.get("type", "active"),
                is_mandatory=skill_data.get("mandatory", False),
                description=skill_data.get("description"),
                description_es=skill_data.get("description_es")
            )
            db.session.add(skill)
            skill_count += 1
    
    # Seed traits
    for trait_data in data.get("traits", []):
        existing = Trait.query.filter_by(name=trait_data["name"]).first()
        if not existing:
            trait = Trait(
                name=trait_data["name"],
                name_es=trait_data.get("name_es"),
                trait_type=trait_data.get("type", "passive"),
                is_mandatory=trait_data.get("mandatory", False),
                description=trait_data.get("description"),
                description_es=trait_data.get("description_es")
            )
            db.session.add(trait)
            trait_count += 1
    
    db.session.commit()
    return skill_count, trait_count


def seed_skills():
    """Legacy function - calls new seed_skills_and_traits."""
    skill_count, trait_count = seed_skills_and_traits()
    return skill_count + trait_count


def seed_races_and_positions():
    """Seed Blood Bowl races and their positions from JSON data."""
    json_path = get_data_path("teams.json")
    
    if not os.path.exists(json_path):
        print(f"  Warning: teams.json not found at {json_path}")
        return 0, 0
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    race_count = 0
    position_count = 0
    
    for team_data in data.get("teams", []):
        # Check if race exists
        race = Race.query.filter_by(name=team_data["name"]).first()
        
        # Serialize special rules to JSON
        special_rules = team_data.get("special_rules", [])
        special_rules_json = json.dumps(special_rules) if special_rules else None
        
        # Serialize league types to JSON
        league_types = team_data.get("league_types", [])
        league_types_json = json.dumps(league_types) if league_types else None
        
        if not race:
            race = Race(
                name=team_data["name"],
                description=team_data.get("description", ""),
                reroll_cost=team_data.get("reroll_cost", 50000),
                apothecary_allowed=team_data.get("apothecary_allowed", True),
                tier=team_data.get("tier", 2),
                special_rules=special_rules_json,
                league_types=league_types_json
            )
            db.session.add(race)
            db.session.flush()  # Get the race ID
            race_count += 1
        else:
            # Update existing race's special rules if changed
            if race.special_rules != special_rules_json:
                race.special_rules = special_rules_json
            # Update existing race's league types if changed
            if race.league_types != league_types_json:
                race.league_types = league_types_json
        
        # Add positions
        for pos_data in team_data.get("positions", []):
            existing = Position.query.filter_by(race_id=race.id, name=pos_data["name"]).first()
            if not existing:
                # Handle passing value (0 means no passing)
                passing_val = pos_data.get("pa")
                if passing_val == 0:
                    passing_val = None
                
                # Convert skills array to comma-separated string
                skills_str = ", ".join(pos_data.get("skills", []))
                
                position = Position(
                    race_id=race.id,
                    name=pos_data["name"],
                    movement=pos_data["ma"],
                    strength=pos_data["st"],
                    agility=pos_data["ag"],
                    passing=passing_val,
                    armor=pos_data["av"],
                    cost=pos_data["cost"],
                    max_count=pos_data["max"],
                    primary_skills=pos_data.get("primary", "G"),
                    secondary_skills=pos_data.get("secondary", ""),
                    starting_skills=skills_str
                )
                db.session.add(position)
                position_count += 1
    
    db.session.commit()
    return race_count, position_count


def seed_star_players():
    """Seed Blood Bowl star players from JSON data."""
    json_path = get_data_path("star_players.json")
    
    if not os.path.exists(json_path):
        print(f"  Warning: star_players.json not found at {json_path}")
        return 0
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    star_count = 0
    
    for sp_data in data.get("star_players", []):
        # Check if star player exists
        star = StarPlayer.query.filter_by(name=sp_data["name"]).first()
        if not star:
            # Handle passing value (0 means no passing)
            passing_val = sp_data.get("pa")
            if passing_val == 0:
                passing_val = None
            
            # Convert skills array to comma-separated string
            skills_str = ", ".join(sp_data.get("skills", []))
            
            # Convert special abilities to pipe-separated string
            special_str = "|".join(sp_data.get("special_abilities", []))
            
            star = StarPlayer(
                name=sp_data["name"],
                cost=sp_data["cost"],
                movement=sp_data["ma"],
                strength=sp_data["st"],
                agility=sp_data["ag"],
                passing=passing_val,
                armor=sp_data["av"],
                skills=skills_str,
                special_abilities=special_str
            )
            db.session.add(star)
            db.session.flush()  # Get the star ID
            
            # Associate with races
            for team_name in sp_data.get("teams", []):
                race = Race.query.filter_by(name=team_name).first()
                if race and race not in star.available_to_races:
                    star.available_to_races.append(race)
            
            star_count += 1
    
    db.session.commit()
    return star_count


def seed_all():
    """Run all seed functions."""
    print("Seeding skills and traits from skills.json...")
    skill_count, trait_count = seed_skills_and_traits()
    print(f"  Added {skill_count} skills and {trait_count} traits")
    
    print("Seeding races and positions from teams.json...")
    race_count, position_count = seed_races_and_positions()
    print(f"  Added {race_count} races and {position_count} positions")
    
    print("Seeding star players from star_players.json...")
    star_count = seed_star_players()
    print(f"  Added {star_count} star players")
    
    print("Seeding complete!")


def clear_and_reseed():
    """Clear existing seed data and reseed (useful for updates)."""
    print("Clearing existing data...")
    
    # Delete in reverse dependency order
    StarPlayer.query.delete()
    Position.query.delete()
    Race.query.delete()
    Trait.query.delete()
    Skill.query.delete()
    
    db.session.commit()
    print("  Cleared all seed data")
    
    # Reseed
    seed_all()
