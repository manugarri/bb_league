"""Seed data for Blood Bowl races, positions, skills, and star players."""
import json
import os
from app.extensions import db
from app.models import Race, Position, Skill, StarPlayer


def get_data_path(filename: str) -> str:
    """Get the path to a data file."""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "data", filename)


def seed_skills():
    """Seed Blood Bowl skills."""
    skills_data = [
        # General Skills
        {"name": "Block", "category": "General", "description": "Adds block die result options"},
        {"name": "Dauntless", "category": "General", "description": "Roll D6 + ST vs opponent ST when blocking"},
        {"name": "Dirty Player (+1)", "category": "General", "description": "+1 to Armor/Injury roll when fouling"},
        {"name": "Dirty Player (+2)", "category": "General", "description": "+2 to Armor/Injury roll when fouling"},
        {"name": "Fend", "category": "General", "description": "Opponent cannot follow up after blocking you"},
        {"name": "Frenzy", "category": "General", "description": "Must follow up and make second block if first succeeds"},
        {"name": "Kick", "category": "General", "description": "Move kick-off ball after placement"},
        {"name": "Pro", "category": "General", "description": "Re-roll any dice roll on 3+"},
        {"name": "Shadowing", "category": "General", "description": "Follow opponent when they dodge away"},
        {"name": "Strip Ball", "category": "General", "description": "Force fumble on pushback vs ball carrier"},
        {"name": "Sure Hands", "category": "General", "description": "Re-roll failed pick-up, ball cannot be stripped"},
        {"name": "Tackle", "category": "General", "description": "Opponent cannot use Dodge skill"},
        {"name": "Wrestle", "category": "General", "description": "Both Down result places both players prone"},
        {"name": "Brawler", "category": "General", "description": "Re-roll Both Down on blocks"},
        {"name": "Drunkard", "category": "General", "description": "Rush attempts only succeed on 4+"},
        
        # Agility Skills
        {"name": "Catch", "category": "Agility", "description": "Re-roll failed catch"},
        {"name": "Diving Catch", "category": "Agility", "description": "Catch in adjacent square, +1 to catch"},
        {"name": "Diving Tackle", "category": "Agility", "description": "Dive to tackle adjacent dodger"},
        {"name": "Dodge", "category": "Agility", "description": "Re-roll failed dodge, ignore Defender Stumbles"},
        {"name": "Defensive", "category": "Agility", "description": "+1 to dodge rolls when leaving tackle zones"},
        {"name": "Jump Up", "category": "Agility", "description": "Stand up for free"},
        {"name": "Leap", "category": "Agility", "description": "Jump over players"},
        {"name": "Safe Pair of Hands", "category": "Agility", "description": "Ball doesn't bounce on failed catch"},
        {"name": "Side Step", "category": "Agility", "description": "Choose push back direction"},
        {"name": "Sneaky Git", "category": "Agility", "description": "Only sent off on double when fouling"},
        {"name": "Sprint", "category": "Agility", "description": "+1 to GFI rolls"},
        {"name": "Sure Feet", "category": "Agility", "description": "Re-roll failed GFI"},
        {"name": "Sidestep", "category": "Agility", "description": "Choose push back direction"},
        
        # Strength Skills
        {"name": "Arm Bar", "category": "Strength", "description": "-1 to dodge/leap when leaving tackle zone"},
        {"name": "Break Tackle", "category": "Strength", "description": "Use ST instead of AG for dodge"},
        {"name": "Grab", "category": "Strength", "description": "Push opponent to any adjacent square"},
        {"name": "Guard", "category": "Strength", "description": "Assists count even when in tackle zones"},
        {"name": "Juggernaut", "category": "Strength", "description": "Ignore defender skills on Blitz"},
        {"name": "Mighty Blow (+1)", "category": "Strength", "description": "+1 to Armor/Injury roll when blocking"},
        {"name": "Mighty Blow (+2)", "category": "Strength", "description": "+2 to Armor/Injury roll when blocking"},
        {"name": "Multiple Block", "category": "Strength", "description": "Block two adjacent players"},
        {"name": "Pile Driver", "category": "Strength", "description": "Foul after knocking down opponent"},
        {"name": "Stand Firm", "category": "Strength", "description": "May choose not to be pushed back"},
        {"name": "Strong Arm", "category": "Strength", "description": "+1 to pass/throw teammate range"},
        {"name": "Thick Skull", "category": "Strength", "description": "Only KO'd on 9+"},
        
        # Passing Skills
        {"name": "Accurate", "category": "Passing", "description": "+1 to passing"},
        {"name": "Cannoneer", "category": "Passing", "description": "+1 to throw teammate distance"},
        {"name": "Cloud Burster", "category": "Passing", "description": "Ignore interceptions on long passes"},
        {"name": "Dump-Off", "category": "Passing", "description": "Quick pass when blocked"},
        {"name": "Fumblerooskie", "category": "Passing", "description": "Place ball on ground adjacent"},
        {"name": "Hail Mary Pass", "category": "Passing", "description": "Throw anywhere on pitch"},
        {"name": "Leader", "category": "Passing", "description": "Team gets extra re-roll"},
        {"name": "Nerves of Steel", "category": "Passing", "description": "Ignore tackle zones on pass/catch"},
        {"name": "On the Ball", "category": "Passing", "description": "Move 3 squares at kick-off"},
        {"name": "Pass", "category": "Passing", "description": "Re-roll failed pass"},
        {"name": "Running Pass", "category": "Passing", "description": "Move after quick pass"},
        {"name": "Safe Pass", "category": "Passing", "description": "Fumble only on natural 1"},
        
        # Mutation Skills
        {"name": "Big Hand", "category": "Mutation", "description": "Ignore tackle zones on pick up"},
        {"name": "Claws", "category": "Mutation", "description": "Break armor on 8+"},
        {"name": "Claw", "category": "Mutation", "description": "Break armor on 8+"},
        {"name": "Disturbing Presence", "category": "Mutation", "description": "-1 to pass/catch nearby"},
        {"name": "Extra Arms", "category": "Mutation", "description": "+1 to catch/pick up/intercept"},
        {"name": "Foul Appearance", "category": "Mutation", "description": "Opponent may not block on 1"},
        {"name": "Horns", "category": "Mutation", "description": "+1 ST on Blitz"},
        {"name": "Iron Hard Skin", "category": "Mutation", "description": "Claws don't work against you"},
        {"name": "Monstrous Mouth", "category": "Mutation", "description": "Re-roll failed catch, can't be stripped"},
        {"name": "Prehensile Tail", "category": "Mutation", "description": "-1 to dodge away from you"},
        {"name": "Tentacles", "category": "Mutation", "description": "Prevent opponent leaving tackle zone"},
        {"name": "Two Heads", "category": "Mutation", "description": "+1 to dodge"},
        {"name": "Very Long Legs", "category": "Mutation", "description": "+1 to intercept, +2 to leap"},
        
        # Trait Skills
        {"name": "Animal Savagery", "category": "Trait", "description": "Must roll 2+ or attack own player"},
        {"name": "Always Hungry", "category": "Trait", "description": "May eat teammate when throwing"},
        {"name": "Ball & Chain", "category": "Trait", "description": "Move randomly, knock down anyone hit"},
        {"name": "Bombardier", "category": "Trait", "description": "Throw bombs"},
        {"name": "Bone Head", "category": "Trait", "description": "Roll 2+ or lose tackle zones"},
        {"name": "Chainsaw", "category": "Trait", "description": "Use chainsaw to attack"},
        {"name": "Decay", "category": "Trait", "description": "Applies to injuries suffered"},
        {"name": "Hypnotic Gaze", "category": "Trait", "description": "Stun adjacent player on 2+"},
        {"name": "Kick Team-Mate", "category": "Trait", "description": "Kick stunty player"},
        {"name": "Loner (3+)", "category": "Trait", "description": "Roll 3+ to use team re-roll"},
        {"name": "Loner (4+)", "category": "Trait", "description": "Roll 4+ to use team re-roll"},
        {"name": "Loner (5+)", "category": "Trait", "description": "Roll 5+ to use team re-roll"},
        {"name": "No Hands", "category": "Trait", "description": "Cannot pick up or carry ball"},
        {"name": "Plague Ridden", "category": "Trait", "description": "Killed players become Rotters"},
        {"name": "Pogo Stick", "category": "Trait", "description": "Can leap any distance"},
        {"name": "Projectile Vomit", "category": "Trait", "description": "Vomit on adjacent player"},
        {"name": "Really Stupid", "category": "Trait", "description": "Need adjacent teammate on 4+"},
        {"name": "Regeneration", "category": "Trait", "description": "Regenerate from injury on 4+"},
        {"name": "Right Stuff", "category": "Trait", "description": "Can be thrown by teammate"},
        {"name": "Secret Weapon", "category": "Trait", "description": "Sent off at end of drive"},
        {"name": "Stab", "category": "Trait", "description": "Stabbing attack instead of block"},
        {"name": "Stunty", "category": "Trait", "description": "+1 to dodge, -1 to pass, +1 to injury"},
        {"name": "Swoop", "category": "Trait", "description": "Land anywhere when thrown"},
        {"name": "Take Root", "category": "Trait", "description": "Cannot move after failing roll"},
        {"name": "Throw Team-Mate", "category": "Trait", "description": "Throw stunty teammate"},
        {"name": "Timmm-ber!", "category": "Trait", "description": "Get help standing up"},
        {"name": "Titchy", "category": "Trait", "description": "Dodge easier but easier to knock down"},
        {"name": "Unchannelled Fury", "category": "Trait", "description": "Roll for action, may attack own player"},
        {"name": "Animosity (Goblin)", "category": "Trait", "description": "Roll when passing to Goblins"},
        {"name": "Animosity (Dwarf)", "category": "Trait", "description": "Roll when passing to Dwarfs"},
        {"name": "Animosity (Halfling)", "category": "Trait", "description": "Roll when passing to Halflings"},
        {"name": "Animosity (all team-mates)", "category": "Trait", "description": "Roll when passing to any teammate"},
        {"name": "Animosity (Big Guy)", "category": "Trait", "description": "Roll when passing to Big Guys"},
    ]
    
    created_count = 0
    for skill_data in skills_data:
        skill = Skill.query.filter_by(name=skill_data["name"]).first()
        if not skill:
            skill = Skill(**skill_data)
            db.session.add(skill)
            created_count += 1
    
    db.session.commit()
    return created_count


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
        if not race:
            race = Race(
                name=team_data["name"],
                description=team_data.get("description", ""),
                reroll_cost=team_data.get("reroll_cost", 50000),
                apothecary_allowed=team_data.get("apothecary_allowed", True),
                tier=team_data.get("tier", 2)
            )
            db.session.add(race)
            db.session.flush()  # Get the race ID
            race_count += 1
        
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
    print("Seeding skills...")
    skill_count = seed_skills()
    print(f"  Added {skill_count} skills")
    
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
    Skill.query.delete()
    
    db.session.commit()
    print("  Cleared all seed data")
    
    # Reseed
    seed_all()
