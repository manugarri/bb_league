"""Translation utilities for Blood Bowl data using Flask-Babel."""
from flask import session, has_request_context
from flask_babel import gettext as babel_gettext


def get_current_locale():
    """Get current locale from session."""
    if has_request_context():
        return session.get('language', 'en')
    return 'en'


def _(text):
    """Wrapper for gettext that handles missing request context."""
    if has_request_context():
        return babel_gettext(text)
    return text


def translate_race(name: str, locale: str = None) -> str:
    """Translate a race name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    # Use Flask-Babel's gettext for translation
    return _(name)


def translate_position(name: str, locale: str = None) -> str:
    """Translate a position name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    return _(name)


def translate_skill(name: str, locale: str = None) -> str:
    """Translate a skill name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    return _(name)


def translate_trait(name: str, locale: str = None) -> str:
    """Translate a trait name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    return _(name)


def translate_star_player(name: str, locale: str = None) -> str:
    """Translate a star player name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en':
        return name
    return _(name)


def translate_league_type(name: str, locale: str = None) -> str:
    """Translate a league type name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en' or not name:
        return name
    return _(name)


def get_team_description(race_name: str, locale: str = None) -> str:
    """Get team description in the specified locale using Flask-Babel.
    
    Note: Team descriptions are stored as English msgids in messages.po.
    The race_name is used to look up the English description, which is
    then translated via Flask-Babel.
    """
    if locale is None:
        locale = get_current_locale()
    
    # Map race names to their English descriptions for translation lookup
    descriptions = {
        "Amazon": "In the jungles of Lustria, Amazon teams are squads of warrior women with super-athlete physiques perfect for Blood Bowl. Their innate agility allows them to pierce through defenses, dodging without giving opponents a chance to react.",
        "Amazons": "In the jungles of Lustria, Amazon teams are squads of warrior women with super-athlete physiques perfect for Blood Bowl. Their innate agility allows them to pierce through defenses, dodging without giving opponents a chance to react.",
        "Black Orc": "Black Orcs are the biggest and strongest of all Orcs. Unlike the rest of their race, Black Orcs are much less stupid and don't like getting bogged down in trivial arguments on the pitch. They form their own teams and focus on winning matches.",
        "Black Orcs": "Black Orcs are the biggest and strongest of all Orcs. Unlike the rest of their race, Black Orcs are much less stupid and don't like getting bogged down in trivial arguments on the pitch. They form their own teams and focus on winning matches.",
        "Chaos Chosen": "Blood Bowl is phenomenally popular among followers of Chaos. Most Chaos teams are formed by Beastmen, reinforced by Chosen humans who have been selected by the forces of Chaos, along with Minotaurs, Ogres, and Trolls.",
        "Chaos Renegade": "Renegade teams are made up of outcasts and rebels who have turned to Chaos. They combine humans, elves, orcs, and other races united in their devotion to the Dark Gods.",
        "Chaos Renegades": "Renegade teams are made up of outcasts and rebels who have turned to Chaos. They combine humans, elves, orcs, and other races united in their devotion to the Dark Gods.",
        "Dark Elf": "Cruel and athletic, Dark Elves combine speed with cruelty. Their players are known for their ruthless approach to the game.",
        "Dwarf": "Slow but incredibly tough, Dwarfs are masters of the attrition game. Their players are known for their Block and Tackle skills.",
        "Elven Union": "Elegant and agile, Elves play a beautiful passing game. They are known for their speed and ball-handling skills.",
        "Goblin": "Goblin teams rely on trickery, traps, and secret weapons. What they lack in strength they make up for in cunning and madness.",
        "Gnomes": "Gnome teams combine cunning with woodland creatures. Their illusionists and beastmasters bring a unique style to the pitch.",
        "Halfling": "Halfling teams are known for their Treemen and indomitable spirit. They may not win much, but they're always entertaining.",
        "High Elf": "The elite of the elven world, High Elves play a precise and elegant passing game. They are arrogant but incredibly skilled.",
        "Human": "Human teams are versatile and balanced. They can adapt to any style of play and are an excellent starting point for new coaches.",
        "Imperial Nobility": "Imperial Nobility teams combine wealth and prestige with Blood Bowl. Their noble blitzers are backed up by ogre bodyguards.",
        "Khorne": "Dedicated to the Blood God, Khorne teams seek bloodshed above all else. They are brutally aggressive.",
        "Lizardmen": "Lizardmen combine the speed of Skinks with the power of Saurus. They are an extremely versatile team.",
        "Necromantic Horror": "Necromantic Horror teams mix undead with creatures like Werewolves and Flesh Golems.",
        "Norse": "Norse teams are aggressive and combative. Their players are known for their Block skill and reckless style.",
        "Nurgle": "Blessed by the Plague God, Nurgle teams are tough and disgusting. Their players are hard to bring down.",
        "Ogre": "Ogre teams are incredibly strong but not very bright. They rely on little Gnoblars to handle the ball.",
        "Old World Alliance": "The Old World Alliance combines Humans, Dwarfs, and Halflings into one team. They offer great versatility.",
        "Orc": "Orc teams are tough and aggressive. They are a balanced team with good blocking and blitz options.",
        "Shambling Undead": "Shambling Undead combine Zombies and Skeletons with fast Ghouls and powerful Mummies.",
        "Skaven": "Skaven teams are extremely fast but fragile. They rely on their speed to outmaneuver opponents.",
        "Snotling": "Snotling teams are tiny, weak, and numerous. They rely on pure chaos and pump wagons.",
        "Tomb Kings": "Tomb Kings are ancient undead from the desert lands. They include Tomb Guardians and mummies.",
        "Underworld Denizens": "Underworld Denizens combine Goblins, Skaven, and mutants into a chaotic team.",
        "Vampire": "Vampire teams have incredibly skilled players but must feed on their Thralls.",
        "Wood Elf": "Wood Elves are the most agile of all elves. They play a spectacular passing and running game.",
        "Bretonnian": "Bretonnian teams combine nobility with peasant players. Knights charge into battle while yeomen hold the line.",
        "Bretonnians": "Bretonnian teams combine nobility with peasant players. Knights charge into battle while yeomen hold the line.",
        "Chaos Dwarf": "Chaos Dwarfs combine the toughness of Dwarfs with the corruption of Chaos. They use Hobgoblins as expendable players.",
        "Chaos Dwarves": "Chaos Dwarfs combine the toughness of Dwarfs with the corruption of Chaos. They use Hobgoblins as expendable players.",
    }
    
    if race_name in descriptions:
        en_desc = descriptions[race_name]
        if locale == 'en':
            return en_desc
        return _(en_desc)
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


def translate_inducement(inducement: dict, locale: str = None) -> dict:
    """Translate an inducement dictionary using Flask-Babel.
    
    Returns a new dict with translated name and description based on locale.
    """
    if locale is None:
        locale = get_current_locale()
    
    result = inducement.copy()
    name = inducement.get('name', '')
    description = inducement.get('description', '')
    cost_note = inducement.get('cost_note', '')
    
    if locale == 'en':
        result['display_name'] = name
        result['display_description'] = description
        if cost_note:
            result['display_cost_note'] = cost_note
    else:
        result['display_name'] = _(name) if name else ''
        result['display_description'] = _(description) if description else ''
        if cost_note:
            result['display_cost_note'] = _(cost_note)
    
    return result


def translate_inducement_name(name: str, locale: str = None) -> str:
    """Translate an inducement name using Flask-Babel."""
    if locale is None:
        locale = get_current_locale()
    if locale == 'en' or not name:
        return name
    return _(name)