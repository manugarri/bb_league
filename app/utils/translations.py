"""Translation utilities for Blood Bowl data."""
import json
from pathlib import Path
from flask import session
from functools import lru_cache


@lru_cache(maxsize=1)
def load_translations():
    """Load translations from JSON file."""
    json_path = Path(__file__).parent.parent / "data" / "translations.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_current_locale():
    """Get current locale from session."""
    return session.get('language', 'en')


def translate_race(name: str, locale: str = None) -> str:
    """Translate a race name."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    
    translations = load_translations()
    races = translations.get('races', {})
    if name in races and locale in races[name]:
        return races[name][locale]
    return name


def translate_position(name: str, locale: str = None) -> str:
    """Translate a position name."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    
    translations = load_translations()
    positions = translations.get('positions', {})
    if name in positions and locale in positions[name]:
        return positions[name][locale]
    return name


def translate_skill(name: str, locale: str = None) -> str:
    """Translate a skill name."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    
    translations = load_translations()
    skills = translations.get('skills', {})
    if name in skills and locale in skills[name]:
        return skills[name][locale]
    return name


def translate_star_player(name: str, locale: str = None) -> str:
    """Translate a star player name."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    
    translations = load_translations()
    star_players = translations.get('star_players', {})
    if name in star_players and locale in star_players[name]:
        return star_players[name][locale]
    return name


def get_team_description(race_name: str, locale: str = None) -> str:
    """Get team description in the specified locale."""
    if locale is None:
        locale = get_current_locale()
    
    translations = load_translations()
    descriptions = translations.get('team_descriptions', {})
    if race_name in descriptions and locale in descriptions[race_name]:
        return descriptions[race_name][locale]
    return ""


def translate_skills_list(skills_str: str, locale: str = None) -> str:
    """Translate a comma-separated list of skills."""
    if not skills_str:
        return skills_str
    
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return skills_str
    
    skills = [s.strip() for s in skills_str.split(',')]
    translated = [translate_skill(s, locale) for s in skills]
    return ', '.join(translated)

