# Blood Bowl League Tracker - Design Log

This document tracks all design decisions and changes made during development.

---

## Table of Contents
1. [Project Setup](#project-setup)
2. [Authentication & Authorization](#authentication--authorization)
3. [League Management](#league-management)
4. [Team Management](#team-management)
5. [Match Recording](#match-recording)
6. [Betting System](#betting-system)
7. [League Points System](#league-points-system)
8. [Internationalization (i18n)](#internationalization-i18n)
9. [Database & Migrations](#database--migrations)
10. [UI/UX Decisions](#uiux-decisions)
11. [CLI Tools](#cli-tools)
12. [Skills and Traits System](#skills-and-traits-system)
13. [Makefile Commands](#makefile-commands)
14. [League Types System](#league-types-system)
15. [Special Rules System](#special-rules-system)
16. [Star Players League Types](#star-players-league-types)
17. [Pre-Match Activities System](#pre-match-activities-system)
18. [Starting Skills Assignment](#starting-skills-assignment)

---

## Project Setup

### Initial Stack
- **Framework**: Flask (Python)
- **Database**: SQLAlchemy ORM with SQLite (development)
- **Package Manager**: uv
- **Frontend**: Bootstrap 5 with custom dark theme
- **Authentication**: Flask-Login with session-based auth

### Dependencies
- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Babel
- Removed Flask-Migrate in favor of `db.create_all()` for simpler setup

---

## Authentication & Authorization

### Login Mechanism
- **Decision**: Changed login from email-based to username-based
- **Reason**: Simpler for users to remember, more common in gaming applications

### Role-Based Access Control
- **Roles**: `admin` and `coach`
- **Admin Privileges**:
  - Only admins can create leagues
  - Admins can edit any match record (including completed matches)
  - Admins can manage any team roster (hire/fire players, purchase items)
  - Admins can edit team assets (treasury, rerolls, fan factor, staff)
  - Admins can delete teams and leagues (with cascade deletion of related data)
  - Admins can join any team to a league (bypasses ownership check)
  
### Route Protection
- **Decision**: All views require authentication
- **Implementation**: Added `@login_required` decorator to all routes
- **Exception**: Language switcher (`/set-language/<lang>`) remains public for login page usage

---

## League Management

### League Creation
- **Restriction**: Only administrators can create leagues
- **Reason**: Prevents proliferation of abandoned leagues, ensures quality control

### League Settings
Added configurable roster rules per league:
- `min_roster_size` (default: 11) - Minimum players required
- `max_roster_size` (default: 16) - Maximum players allowed  
- `allow_star_players` (default: True) - Whether star players can be hired

### Team Registration Validation
When a team requests to join a league:
1. Validates team has at least `min_roster_size` players
2. Validates team doesn't exceed `max_roster_size` players
3. Shows clear error messages in user's language

### Scoring System
Configurable points:
- Win points (default: 3)
- Draw points (default: 1)
- Loss points (default: 0)

---

## Team Management

### Star Players
- **Implementation**: Created `team_star_players` association table
- **Features**:
  - Hire star players available to team's race
  - Release star players (no refund, per Blood Bowl rules)
  - Star player cost deducted from treasury
  - Star player value included in Team Value (TV) calculation
  
### Team Value Calculation
TV includes:
- Active player values
- Star player costs
- Rerolls × race reroll cost
- Assistant coaches × 10,000g
- Cheerleaders × 10,000g
- Apothecary (50,000g if hired)

### Player Value Calculation
Player value = Position cost + Learned skills value + Stat increases

**Learned Skills Value:**
| Skill Type | Value Added |
|------------|-------------|
| Premium skills (Dodge, Mighty Blow, Block, Guard) | 30,000g each |
| Other skills | 20,000g each |

**Stat Increases Value:**
| Stat | Value per +1 |
|------|--------------|
| Movement (MA) | 10,000g |
| Strength (ST) | 20,000g |
| Agility (AG) | 20,000g |
| Armor (AV) | 10,000g |

*Note: Starting skills do not add to player value.*

### Roster Display
Player table shows:
- Number, Name, Position
- Stats (MA, ST, AG, PA, AV)
- Skills (up to 3 badges, "+N" for overflow with Bootstrap popover)
- SPP with level-up indicator
- Career stats (TD, CAS)

### Team Assets Management
Editable team assets (via Edit Team page):
- **Treasury**: Available gold for purchases
- **Rerolls**: Team rerolls (0-8)
- **Fan Factor**: Starting value of 1 (changed from 0)
- **Assistant Coaches**: (0-6)
- **Cheerleaders**: (0-12)
- **Apothecary**: Boolean (if race allows)

**Permissions**:
- Team owners can edit their own team's assets
- Admins can edit any team's assets

### Team/League Deletion
- **Admin only**: Delete button in "Danger Zone" section
- **Cascade deletion**: All related records (players, matches, league entries) deleted
- **Confirmation**: JavaScript confirm dialog before deletion

---

## Match Recording

### Form Validation Fix
- **Issue**: `DataRequired()` validator rejected `0` as valid input
- **Solution**: Changed to `InputRequired()` for all integer fields
- **Affected**: League creation form, match recording form

### Match Result Recording
Two-step process:
1. Record match score, casualties, winnings
2. Record individual player statistics (TD, CAS, completions, interceptions, MVP, injuries)

### SPP Calculation Fix
- **Issue**: `NoneType` error when calculating SPP
- **Solution**: Added `or 0` fallback for all nullable stat fields
```python
spp += (self.touchdowns or 0) * 3
spp += (self.casualties_inflicted or 0) * 2
# etc.
```

### Admin Match Editing
- Admins can edit completed matches
- Regular users cannot modify completed matches

### Bet Resolution on Match Completion
- When a match result is recorded, all pending bets are automatically resolved
- Flash message shows count of resolved bets
- Notifications created for all affected bettors

---

## Betting System

### Overview
Users can place bets on matches they are not participating in. This adds an engaging meta-game layer to league play.

### Betting Rules
1. **Eligibility**: Users can only bet on matches where their team is NOT playing
2. **Limit**: One bet per user per match
3. **Maximum stake**: 50,000 gold per bet
4. **Timing**: Bets can only be placed on scheduled (not yet played) matches

### Bet Types
| Type | Description | Payout Multiplier |
|------|-------------|-------------------|
| `win` | Team wins the match | 2x |
| `td_exact` | Team scores exactly X touchdowns | 5x |
| `cas_exact` | Team inflicts exactly X casualties | 7x |

### Database Models

#### Bet Model (`app/models/bet.py`)
```python
class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    bet_type = db.Column(db.String(50))  # 'win', 'td_exact', 'cas_exact'
    bet_amount = db.Column(db.Integer)
    target_value = db.Column(db.Integer)  # For exact bets
    odds = db.Column(db.Float)
    is_resolved = db.Column(db.Boolean, default=False)
    is_won = db.Column(db.Boolean)
    payout = db.Column(db.Integer)
```

#### BetNotification Model
```python
class BetNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    bet_id = db.Column(db.Integer, db.ForeignKey("bets.id"))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
```

### Bet Resolution Logic
When a match result is recorded (`matches.record` route):
1. `resolve_bets(match)` function is called
2. For each unresolved bet on the match:
   - Determine if bet won based on bet type and match results
   - Calculate payout if won
   - Update user's treasury (add payout for wins)
   - Create notification with win/loss message
3. Commit all changes

### User Interface

#### Placing Bets
- **Location**: Match view page → "Place Bet" button
- **Form**: Interactive cards for bet type, team selection, amount
- **Visual feedback**: Potential winnings calculated in real-time

#### Viewing Bets
- **My Bets page** (`/bets/`):
  - Stats cards: Total Won, Total Lost, Net Balance, At Stake
  - Pending bets section
  - Resolved bets section with win/loss indicators

#### Notifications
- **Badge**: Unread count shown on "Bets" nav link
- **Notifications page** (`/bets/notifications`):
  - List of bet outcome notifications
  - Mark as read functionality
  - Win notifications show 🎉 emoji

### Blueprint Routes (`app/blueprints/bets.py`)
| Route | Method | Description |
|-------|--------|-------------|
| `/bets/` | GET | View all user's bets |
| `/bets/match/<id>/place` | GET, POST | Place bet on match |
| `/bets/notifications` | GET | View bet notifications |
| `/bets/notifications/<id>/read` | POST | Mark notification as read |
| `/bets/<id>` | GET | View single bet details |
| `/bets/<id>/cancel` | POST | Cancel pending bet |

---

## League Points System

### Overview
A comprehensive points system that rewards teams for match results and exceptional performances. Points determine league standings.

### Points Allocation

#### Match Result Points
| Result | Points |
|--------|--------|
| Victory | +3 |
| Draw | +1 |
| Loss | +0 |

#### Bonus Points
| Achievement | Points | Description |
|-------------|--------|-------------|
| High Scoring | +1 | Scoring 3 or more touchdowns in a match |
| High-Scoring Opponent | +1 | When opponent scores 3+ touchdowns against you |
| Brutal | +1 | Causing 3 or more casualties in a match |

### Database Schema Changes

New columns added to `Standing` model (`app/models/league.py`):
```python
# Bonus points tracking
bonus_points = db.Column(db.Integer, default=0)  # Total bonus points
bonus_high_scoring = db.Column(db.Integer, default=0)  # 3+ TD games count
bonus_opponent_high_scoring = db.Column(db.Integer, default=0)  # Games where opponent scored 3+ TDs
bonus_casualties = db.Column(db.Integer, default=0)  # 3+ CAS games count
```

### Standing Update Logic

The `update_from_match()` method now calculates:
1. Base points from match result (win/draw/loss)
2. Bonus for scoring 3+ touchdowns
3. Bonus for opponent scoring 3+ touchdowns (high-scoring game reward)
4. Bonus for causing 3+ casualties

### User Interface

#### Standings Table
- Added **BP** (Bonus Points) column showing bonus points earned
- Tooltip on BP cells shows breakdown (TDs, Opp TDs, CAS bonuses)
- Added "League Points System" explanation card below standings table

#### League View
- Quick standings table now includes BP column
- Teams sorted by total points (base + bonus)

### API Changes

`GET /api/leagues/<id>/standings` now returns:
```json
{
  "standings": [{
    "points": 10,
    "bonus_points": 2,
    "bonus_breakdown": {
      "high_scoring": 1,
      "opponent_high_scoring": 0,
      "casualties": 1
    }
  }]
}
```

### Implementation Notes

1. **Standings Auto-Creation**: The `update_standings()` function in `app/blueprints/matches.py` now creates Standing records if they don't exist (previously only updated existing ones)

2. **Null Safety**: All numeric fields use `(field or 0)` pattern to handle newly created standings with None values

3. **Seed Script Updates**: `scripts/seed_test_data.py` now:
   - Creates Season records for leagues
   - Sets `season_id` on matches
   - Calls `update_standings()` when simulating match results

---

## Internationalization (i18n)

### Supported Languages
- English (en) - default
- Spanish (es)

### Translation Approach
1. **All translations**: Centralized in Flask-Babel's `messages.po` file
2. **Game data**: Custom translation utilities in `app/utils/translations.py` using Flask-Babel's `gettext()`
3. **Flash messages**: Language check with `session.get('language', 'en')`

### Translation Files
- `app/translations/es/LC_MESSAGES/messages.po` - All translations including:
  - UI strings
  - Race names (singular and plural forms)
  - Position names (170+ positions)
  - Skill names (90+ skills)
  - Star player names
  - Special abilities
  - Team descriptions
  - Special rules and league types

### Translation Utilities (`app/utils/translations.py`)
| Function | Purpose |
|----------|---------|
| `translate_race(name, locale)` | Translate race names |
| `translate_position(name, locale)` | Translate position names |
| `translate_skill(name, locale)` | Translate skill names |
| `translate_star_player(name, locale)` | Translate star player names |
| `translate_skills_list(skills_str, locale)` | Translate comma-separated skill lists |
| `get_team_description(race_name, locale)` | Get translated team description |

### Language Switcher
- Accessible from navbar dropdown
- Stores preference in session
- Works on login page (public route)

### Migration from JSON to Babel (December 2025)
- **Removed**: `app/data/translations.json` - all translations consolidated
- **Updated**: Translation utilities now use `flask_babel.gettext()` instead of JSON loading
- **Added**: `has_request_context()` checks for graceful fallback outside request context
- **Benefit**: Single source of truth, standard tooling support (`pybabel extract/update/compile`)

---

## Database & Migrations

### Migration Removal
- **Decision**: Removed Flask-Migrate entirely
- **Reason**: Simpler setup, database created from models via `db.create_all()`
- **Trade-off**: Must reset database for schema changes

### Database Reset Process
```bash
make reset  # Deletes DB, creates fresh tables, seeds data
```

### Seeding
- Races with positions from `app/data/teams.json`
- Star players from `app/data/star_players.json`
- Skills seeded from team data
- Admin user creation via CLI or `upsert_user.py` script

---

## UI/UX Decisions

### Theme
- Dark theme with Blood Bowl aesthetic
- Colors: Blood red (`#8B0000`), Gold (`#DAA520`)
- Fonts: Orbitron (headings), Rajdhani (body)

### CSRF Protection
All POST forms require CSRF token:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

Forms using WTForms use `{{ form.hidden_tag() }}` instead.

### Tables with Missing CSRF Tokens Fixed
- Fire player form
- Purchase forms (reroll, assistant coach, cheerleader, apothecary)
- Join league form
- Approve/reject team forms

### Level Up Indicator
- SPP highlighted in gold when level up available
- Arrow icon (↑) shown next to SPP
- Tooltip explains level up is available

### Skill Display
- Skills shown as badges
- Maximum 3 skills displayed inline
- "+N" badge for additional skills with hover tooltip

---

## CLI Tools

### User Management Script
`scripts/upsert_user.py`:
- Create new users with username and password
- Update existing user passwords
- Grant/revoke admin privileges
- Makefile integration: `make upsert-user USERNAME=x PASSWORD=y ADMIN=1`

### Test Data Seeding Script
`scripts/seed_test_data.py`:
- Creates test users for development/testing:
  - `admin:admin` (Administrator)
  - `user1:user1` (Coach)
  - `user2:user2` (Coach)
- Creates a team for each user with 4 players
- Creates a test league (`test-league`) with `min_roster_size=4`
- Enrolls all teams in the league
- Idempotent: Safe to run multiple times
- Makefile integration: `make seed-test-data`

### Flask CLI Commands
- `flask seed` - Seed database with game data
- `flask seed --clear` - Clear and reseed
- `flask create-admin <username> <email> <password>` - Create admin user

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install-dev` | Install dependencies with uv (Windows) |
| `make install-prod` | Install dependencies with uv (Linux/Ubuntu) |
| `make run-dev` | Start application in debug mode (Windows) |
| `make run-prod` | Start application with gunicorn (Linux/Ubuntu) |
| `make seed` | Seed database with game data (races, skills, star players) |
| `make seed-test-data` | Seed test users, teams, and league for development |
| `make reset` | Delete and recreate database with seed data |
| `make clean` | Remove generated files |
| `make test` | Run pytest |
| `make upsert-user` | Create/update user |
| `make db-export` | Export entire database to JSON file |
| `make db-import` | Import database from JSON file |
| `make export-teams` | Export teams to JSON file |
| `make import-teams` | Import teams from JSON (with optional RESET=1) |
| `make export-users` | Export users to JSON file |
| `make import-users` | Import users from JSON (with optional RESET=1) |
| `make export-leagues` | Export leagues to JSON file |
| `make import-leagues` | Import leagues from JSON (with optional RESET=1) |
| `make export-bets` | Export bets to JSON file |
| `make import-bets` | Import bets from JSON (with optional RESET=1) |

### Database Export/Import Scripts
Located in `scripts/`:
- `db_export_import.py` - Full database backup/restore
- `teams_export_import.py` - Teams with players and star players
- `users_export_import.py` - Users with passwords (hashed)
- `leagues_export_import.py` - Leagues with seasons and standings
- `bets_export_import.py` - Bets and bet notifications

---

## League Types System

### Overview
Teams can be affiliated with specific league types based on their race. This follows the official Blood Bowl 3rd Edition rulebook guidelines.

### Implementation
- **Data storage**: `league_types` JSON array stored in `Race` model
- **Team affiliation**: `league_type` column in `Team` model (nullable)
- **Source**: League types extracted from `pdfs/reglamento-bb3-teams.pdf`

### Available League Types
| League Type | Spanish Translation |
|-------------|---------------------|
| Lustrian Superleague | Superliga Lustriana |
| Chaos Championship | Campeonato del Caos |
| Badlands Brawl | Reyerta en las Yermas |
| World's Edge Superleague | Superliga de los Confines del Mundo |
| Elven Kingdoms League | Liga de los Reinos Elficos |
| Sylvanian Spotlight | Liga Silvania |
| Old World Classic | Clasica del Viejo Mundo |
| Underworld Challenge | Desafio del Inframundo |

### User Interface
- **Team Creation**: Dynamic dropdown showing available league types for selected race
- **Team Edit**: Dropdown to change/set league type
- **Team View**: Badge displaying current league type

### Race Method
```python
Race.get_league_types() -> list[str]
```
Returns list of available league types for the race (parsed from JSON).

---

## Special Rules System

### Overview
Each race has special rules that apply to all teams of that race. These are defined in `teams.json` and displayed on team view pages.

### Implementation
- **Data storage**: `special_rules` JSON array stored in `Race` model
- **Source**: Special rules extracted from `pdfs/reglamento-bb3-team-rules.pdf`
- **Translations**: All special rule names and descriptions in `messages.po`

### Example Special Rules
| Rule | Description |
|------|-------------|
| Brawlin' Brutes | SPP earned differently (3 for CAS, 2 for TD) |
| Bribery and Corruption | Re-roll failed Argue the Call once per match |
| Favoured of Khorne | Can re-roll a single die when blocking |
| Badland Brawl | Once per game, re-roll Armour roll |

### Race Method
```python
Race.get_special_rules() -> list[dict]
```
Returns list of special rules with `name` and `description` keys.

---

## Star Players League Types

### Overview
Star players are now associated with specific league types, determining which leagues they can be hired for. This follows the official Blood Bowl 3rd Edition rulebook ("JUEGA PARA" / "Plays For" section for each star player).

### Implementation
- **Data storage**: `league_types` JSON array added to each star player in `app/data/star_players.json`
- **Source**: League type affiliations extracted from `pdfs/reglamento-bb3-star-players.pdf`

### Star Player League Affiliations

| Star Player | League Types |
|-------------|--------------|
| Morg 'n' Thorg | All leagues (universal) |
| Griff Oberwald | Old World Classic |
| Hakflem Skuttlespike | Underworld Challenge |
| Varag Ghoul-Chewer | Badlands Brawl |
| Deeproot Strongbranch | Halfling Thimble Cup, Elven Kingdoms League, Old World Classic |
| Kreek Rustgouger | Underworld Challenge |
| Roxanna Darknail | Lustrian Superleague, Elven Kingdoms League |
| Grim Ironjaw | World's Edge Superleague, Old World Classic |
| Zug | Old World Classic |
| Wilhelm Chaney | Sylvanian Spotlight |
| Bomber Dribblesnot | Badlands Brawl, Underworld Challenge |
| Ripper Bolgrot | Badlands Brawl, Underworld Challenge |
| Karla Von Kill | Lustrian Superleague, Old World Classic |
| Helmut Wulf | Old World Classic |
| Glart Smashrip | Chaos Championship, Underworld Challenge, Favoured of Nurgle |
| Eldril Sidewinder | Elven Kingdoms League |
| Mighty Zug | Old World Classic |
| Skitter Stab-Stab | Underworld Challenge |
| Lord Borak the Despoiler | Chaos Championship, Favoured of Khorne, Favoured of Nurgle |
| Fungus the Loon | Badlands Brawl, Underworld Challenge |
| Count Luthor Von Drakenborg | Sylvanian Spotlight |
| Grak and Crumbleberry | Halfling Thimble Cup, Old World Classic |
| Rashnak Backstabber | Elven Kingdoms League, Underworld Challenge |
| Barik Farblast | World's Edge Superleague, Old World Classic |
| Scrappa Sorehead | Badlands Brawl, Underworld Challenge |
| Akhorne the Squirrel | Halfling Thimble Cup, Elven Kingdoms League |

### JSON Structure
```json
{
  "name": "Griff Oberwald",
  "cost": 320000,
  "skills": [...],
  "teams": ["Human", "Bretonnian", "Imperial Nobility", "Old World Alliance"],
  "league_types": ["Old World Classic"]
}
```

---

## Pre-Match Activities System

### Overview
Pre-match activities allow coaches to prepare their teams before a match begins. This includes purchasing inducements - temporary bonuses and special hires that last for a single match.

### Workflow
1. **Match Scheduled**: When a match is created, both teams can access pre-match activities
2. **Inducement Selection**: Each coach can purchase inducements using:
   - **Petty Cash**: Free gold given to the team with lower Team Value (TV equals the difference)
   - **Team Treasury**: Additional gold from the team's treasury
3. **Submission**: Once satisfied, coaches submit their inducement selections
4. **Match Ready**: When both teams have submitted, the match can begin

### Database Models

#### PreMatchSubmission (`app/models/prematch.py`)
```python
class PreMatchSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    inducements_submitted = db.Column(db.Boolean, default=False)
    inducements_submitted_at = db.Column(db.DateTime)
    total_inducements_cost = db.Column(db.Integer, default=0)
```

#### MatchInducement (`app/models/prematch.py`)
```python
class MatchInducement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    inducement_id = db.Column(db.String(64))  # References inducements.json
    inducement_name = db.Column(db.String(128))
    quantity = db.Column(db.Integer, default=1)
    cost_per_unit = db.Column(db.Integer)
    total_cost = db.Column(db.Integer)
    extra_data = db.Column(db.Text)  # JSON for star_player_id, etc.
```

### Match Model Updates
Added to `Match` model:
- `home_prematch_ready` (Boolean) - Home team submitted pre-match
- `away_prematch_ready` (Boolean) - Away team submitted pre-match
- `is_prematch_complete` (Property) - Both teams ready
- `can_record_result` (Property) - Pre-match complete or in progress

### Available Inducements
Based on Blood Bowl 3rd Edition rules (`pdfs/reglamento-bb3-inducements.pdf`):

| Inducement | Cost | Max | Notes |
|------------|------|-----|-------|
| Prayers to Nuffle | 10,000g | 3 | Roll D16 for random effect |
| Part-time Assistants | 20,000g | 5 | +1 to assistant coaches |
| Temporary Cheerleaders | 5,000g | 5 | +1 to cheerleaders |
| Team Mascot | 25,000g | 1 | Extra team re-roll |
| Weather Mage | 25,000g | 1 | Re-roll weather table |
| Bloodweiser Kegs | 50,000g | 2 | +1 to KO recovery |
| Bribe | 100,000g (50,000g*) | 3 (6*) | Avoid send-off |
| Extra Training | 100,000g | 8 | Extra team re-roll |
| Mortuary Assistant | 100,000g | 1 | Undead only |
| Plague Doctor | 100,000g | 1 | Nurgle only |
| Riotous Rookies | 150,000g | 1 | Low Cost Linemen only |
| Wandering Apothecary | 100,000g | 2 | Apothecary-allowed only |
| Halfling Master Chef | 300,000g (100,000g*) | 1 | Steal re-rolls |
| Biased Referee | 120,000g (80,000g*) | 1 | Ref favors your team |
| Josef Bugman | 100,000g | 1 | Famous staff member |
| Mercenary Player | 30,000g + cost | 3 | Temporary player |
| Star Player | Variable | 2 | Legendary mercenary |
| Wizard | 150,000g | 1 | Fireball or Lightning |

*Discounted for teams with specific special rules

### Petty Cash Calculation
```python
def calculate_petty_cash(home_team, away_team) -> tuple:
    home_tv = home_team.calculate_tv()
    away_tv = away_team.calculate_tv()
    diff = abs(home_tv - away_tv)
    
    if home_tv < away_tv:
        return (diff, 0)  # Home gets petty cash
    elif away_tv < home_tv:
        return (0, diff)  # Away gets petty cash
    return (0, 0)
```

### Blueprint Routes (`app/blueprints/prematch.py`)
| Route | Method | Description |
|-------|--------|-------------|
| `/prematch/match/<id>` | GET | Pre-match overview |
| `/prematch/match/<id>/team/<team_id>/inducements` | GET, POST | Manage inducements |
| `/prematch/match/<id>/team/<team_id>/skip` | POST | Skip without inducements |
| `/prematch/api/match/<id>/inducements` | GET | API for inducements data |

### User Interface
- **Pre-match Overview**: Shows both teams' status, petty cash, and purchased inducements
- **Inducements Page**: Interactive UI for browsing and purchasing inducements
- **Star Players Section**: Dedicated section for hiring star players
- **Budget Tracker**: Real-time display of remaining budget

### Integration with Match Flow
1. Match view shows pre-match status when scheduled
2. "Pre-Match Activities" button visible for scheduled matches
3. Record Result button only enabled when pre-match complete
4. Inducements displayed on completed match view

### Data File
`app/data/inducements.json` contains:
- All inducement definitions with English/Spanish names and descriptions
- Cost, max quantity, availability rules
- Race/special rule discounts
- Prayers to Nuffle table

### Translations
All inducement names and UI strings translated in `messages.po`

---

## Future Considerations

### Not Yet Implemented
- Star player hiring validation against league's `allow_star_players` setting
- Deflections stat in player stats form
- Tournament bracket support
- API authentication with JWT
- Bet cancellation before match starts
- Betting statistics and leaderboards
- User treasury management (separate from team treasury)
- Mercenary player hiring in inducements (position selection)
- Prayers to Nuffle random roll implementation

### Known Limitations
- Database must be reset for schema changes (no migrations)
- Star players can be hired permanently to roster OR as match inducements
- No image upload for teams/players
- User treasury for betting is currently at 0 (needs initial funding mechanism)

---

## Skills and Traits System

### Data Source
Skills and traits extracted from the official Blood Bowl 3rd Edition rulebook (PDF).

### Skills JSON Structure (`app/data/skills.json`)
```json
{
  "skill_categories": [...],
  "skills": [
    {
      "name": "Block",
      "name_es": "Placar",
      "category": "G",  // A, S, G, M, P, E
      "type": "active|passive",
      "mandatory": false,  // Skills marked with *
      "description": "English description",
      "description_es": "Spanish description"
    }
  ],
  "traits": [...]
}
```

### Skill Categories
| Code | English | Spanish |
|------|---------|---------|
| A | Agility | Agilidad |
| S | Strength | Fuerza |
| G | General | Generales |
| M | Mutation | Mutación |
| P | Passing | Pase |
| E | Extraordinary | Triquiñuelas |

### Database Models
- `Skill` - Learnable abilities with category, type, translations
- `Trait` - Innate abilities that cannot be learned
- `PlayerSkill` - Association table linking players to learned skills
- `PlayerTrait` - Association table linking players to traits

### Player Methods for Skills
- `player.get_skill_list()` - Returns list of skill names
- `player.get_trait_list()` - Returns list of trait names
- `player.get_all_abilities()` - Returns dict with skills and traits
- `player.add_skill(skill, is_starting)` - Add a skill to player
- `player.add_trait(trait)` - Add a trait to player
- `player.assign_starting_skills()` - Assign starting skills/traits from position

---

## Starting Skills Assignment

### Overview
When players are hired, they automatically receive the starting skills and traits defined for their position. This mirrors the Blood Bowl rules where each position type comes with specific abilities.

### Implementation

#### Automatic Skill Assignment on Hire
When a player is hired through the `hire_player` route:
1. Player is created with stats from position
2. `player.assign_starting_skills()` is called
3. Starting skills/traits from `Position.starting_skills` are parsed
4. Each skill/trait is looked up in the database and assigned with `is_starting=True`

#### Skill/Trait Matching Logic
The `assign_starting_skills()` method handles:
- **Exact matches**: Skills like "Block", "Dodge" are matched directly
- **Parameterized abilities**: Skills like "Loner (4+)" are matched to "Loner (X+)" in the database
- **Missing abilities**: Logged as warnings but don't fail the operation

#### Database Models
- `PlayerSkill.is_starting` - Boolean flag indicating if skill came with position
- `PlayerTrait.is_starting` - Boolean flag indicating if trait came with position

### Backfill Script
For existing players without starting skills:

```bash
# Preview what would be changed
make backfill-skills DRY_RUN=1

# Apply changes
make backfill-skills
```

Script location: `scripts/backfill_player_skills.py`

### Skills Added to skills.json
The following skills/traits were added to support all position abilities:
- **Skills**: Hit and Run, Breathe Fire, My Ball, Trickster
- **Traits**: Animal Savagery, Drunkard, Hate (X), Plague Ridden

---

## League Schedule Management (Admin)

### Overview
Administrators can now manage league schedules by adding and deleting matches directly from the schedule view. This allows for flexible schedule management without needing to regenerate the entire schedule.

### Features

#### Delete Scheduled Matches
- **Restriction**: Only administrators can delete matches
- **Limitation**: Cannot delete completed matches (only scheduled, in_progress, prematch, or cancelled)
- **Confirmation**: JavaScript confirm dialog before deletion
- **Cascade**: All related pre-match submissions and inducements are deleted

#### Add New Scheduled Matches
- **Restriction**: Only administrators can add matches
- **Requirements**: At least 2 approved teams must be in the league
- **Validation**: 
  - Both teams must be registered and approved in the league
  - Home and away teams must be different
- **Fields**: Home team, Away team, Round number

### Routes Added (`app/blueprints/leagues.py`)
| Route | Method | Description |
|-------|--------|-------------|
| `/leagues/<id>/schedule/add` | POST | Add a new scheduled match |
| `/leagues/<id>/schedule/<match_id>/delete` | POST | Delete a scheduled match |

### Form Added (`app/forms/league.py`)
```python
class ScheduleMatchForm(FlaskForm):
    home_team_id = SelectField("Home Team", coerce=int)
    away_team_id = SelectField("Away Team", coerce=int)
    round_number = IntegerField("Round Number", default=1)
```

### UI Changes
- **Schedule page**: 
  - Added "Add Match" button (visible to admins only)
  - Added delete button for each non-completed match (visible to admins only)
  - Modal dialog for adding new matches
  - Confirmation dialog before deleting matches

### Translations Added
| English | Spanish |
|---------|---------|
| Add Match | Añadir Partido |
| Delete Match | Eliminar Partido |
| Are you sure you want to delete this match? | ¿Estás seguro de que quieres eliminar este partido? |
| No schedule generated | No hay calendario generado |
| The league schedule hasn't been generated yet. | El calendario de la liga aún no se ha generado. |
| Round Number | Número de Jornada |
| At least 2 approved teams are required to create matches. | Se necesitan al menos 2 equipos aprobados para crear partidos. |

### Permissions
- **View schedule**: All authenticated users
- **Add match**: Administrators only
- **Delete match**: Administrators only (non-completed matches)

---

## Player Stats Delta Storage

### Overview
Changed player stat storage from absolute values to delta/modifier values. Instead of storing the full stat values for each player, we now store only the difference (delta) from the base position stats. This reduces data redundancy since most players have the same stats as their position.

### Schema Change

**Old Schema (absolute values):**
```python
class Player(db.Model):
    movement = db.Column(db.Integer)   # e.g., 6
    strength = db.Column(db.Integer)   # e.g., 3
    agility = db.Column(db.Integer)    # e.g., 3
    passing = db.Column(db.Integer)    # e.g., 4
    armor = db.Column(db.Integer)      # e.g., 8
```

**New Schema (delta values):**
```python
class Player(db.Model):
    movement_mod = db.Column(db.Integer, default=0)  # e.g., 0 (no change from base)
    strength_mod = db.Column(db.Integer, default=0)  # e.g., -1 (injury reduced)
    agility_mod = db.Column(db.Integer, default=0)   # e.g., +1 (improvement)
    passing_mod = db.Column(db.Integer, default=0)
    armor_mod = db.Column(db.Integer, default=0)

    @property
    def movement(self) -> int:
        """Get effective movement (base + modifier)."""
        return self.position.movement + (self.movement_mod or 0)
    # ... similar properties for other stats
```

### Benefits
1. **Reduced redundancy**: Most players have modifier values of 0
2. **Clear tracking**: Easy to see which players have been modified (injuries/improvements)
3. **Simpler calculations**: Value calculations directly use modifiers
4. **Position changes**: If position stats change, all players automatically reflect this

### Migration
- Migration file: `migrations/versions/abd97c1d9d6b_player_stats_delta_storage.py`
- Handles both fresh databases and existing data conversion
- Calculates deltas: `delta = absolute_stat - position_base_stat`
- Supports downgrade to restore absolute values

### Updated Files
- `app/models/player.py`: Changed stat columns to modifiers, added computed properties
- `app/blueprints/teams.py`: Updated player hiring (no longer sets absolute stats)
- `app/blueprints/matches.py`: Updated injury application to modify deltas
- `scripts/seed_test_data.py`: Updated player creation
- `scripts/teams_export_import.py`: Updated to export/import both formats

---

## Database Migrations with Flask-Migrate

### Overview
Re-introduced Flask-Migrate for database schema management, enabling version-controlled migrations.

### Setup
- Added `flask-migrate>=4.0.0` to dependencies
- Initialized migrations folder: `migrations/`
- Configured in `app/extensions.py` and `app/__init__.py`

### Makefile Commands

| Command | Description |
|---------|-------------|
| `make migrate` | Apply pending migrations |
| `make migrate MSG="message"` | Create new migration with message and apply it |
| `make migrate-init` | Initialize migrations folder (run once for new projects) |

### Usage Examples
```bash
# Apply pending migrations
make migrate

# Create a new migration after model changes
make migrate MSG="add user preferences table"

# Initialize migrations (new project setup)
make migrate-init
```

### Migration Files
Located in `migrations/versions/`:
- `abd97c1d9d6b_player_stats_delta_storage.py` - Player stats delta storage conversion

---

*Last updated: January 10, 2026*

