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
7. [Internationalization (i18n)](#internationalization-i18n)
8. [Database & Migrations](#database--migrations)
9. [UI/UX Decisions](#uiux-decisions)
10. [CLI Tools](#cli-tools)
11. [Skills and Traits System](#skills-and-traits-system)

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

## Internationalization (i18n)

### Supported Languages
- English (en) - default
- Spanish (es)

### Translation Approach
1. **Static UI text**: Flask-Babel with `_()` function
2. **Game data**: Custom translation utilities (`tr_race()`, `tr_position()`, `tr_skill()`, `tr_star()`)
3. **Flash messages**: Language check with `session.get('language', 'en')`

### Translation Files
- `app/translations/es/LC_MESSAGES/messages.po` - UI strings
- `app/data/translations.json` - Game-specific translations (races, positions, skills, star players)

### Language Switcher
- Accessible from navbar dropdown
- Stores preference in session
- Works on login page (public route)

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
| `make install` | Install dependencies with uv |
| `make run` | Start application |
| `make dev` | Start in debug mode |
| `make seed` | Seed database with game data (races, skills, star players) |
| `make seed-test-data` | Seed test users, teams, and league for development |
| `make reset` | Delete and recreate database with seed data |
| `make clean` | Remove generated files |
| `make test` | Run pytest |
| `make upsert-user` | Create/update user |
| `make update-translations` | Extract translatable strings |
| `make compile-translations` | Compile .po to .mo files |

---

## Future Considerations

### Not Yet Implemented
- Star player hiring validation against league's `allow_star_players` setting
- Deflections stat in player stats form
- Match-based star player hiring (vs permanent roster)
- Tournament bracket support
- API authentication with JWT
- Bet cancellation before match starts
- Betting statistics and leaderboards
- User treasury management (separate from team treasury)

### Known Limitations
- Database must be reset for schema changes (no migrations)
- Star players are permanently hired to roster (not per-match)
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

---

*Last updated: December 14, 2025*

