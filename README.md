# Blood Bowl League Tracker

A web application to manage Blood Bowl leagues and tournaments. Track your teams, record match results, view standings, and analyze player/team statistics.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)

## Features

### Team Management
- Create teams from official Blood Bowl races
- Manage player rosters (hire, fire, rename)
- Track player statistics (SPP, skills, injuries)
- Manage team treasury and team value
- Player progression and skill selection

### League Management
- Round-robin league format
- Automatic schedule generation
- Standings calculation with customizable scoring
- Registration approval workflow
- Season tracking

### Match Recording
- Record final scores
- Track individual player performance
- Casualties, completions, interceptions
- MVP selection
- Automatic SPP distribution
- Injury tracking

### Statistics & Analytics
- League standings with tiebreakers
- Player leaderboards
- Team statistics
- Historical match data

## Tech Stack

- **Backend**: Flask (Python 3.11+)
- **Database**: SQLite (dev) / PostgreSQL (production)
- **ORM**: Flask-SQLAlchemy
- **Authentication**: Flask-Login + Flask-JWT-Extended
- **Frontend**: Bootstrap 5, Jinja2
- **Package Manager**: uv

## Installation

### Prerequisites

- Python 3.11 or higher
- uv package manager (recommended) or pip

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd blood_bowl_league_tracker
   ```

2. **Create and activate virtual environment**
   ```bash
   # Using uv (recommended)
   uv venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   
   # Or using standard venv
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   # Using uv
   uv pip install -e .
   
   # Or using pip
   pip install -e .
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file
   copy .env.example .env  # Windows
   cp .env.example .env    # Linux/Mac
   
   # Edit .env with your settings
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-here
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Seed initial data (races, positions, skills)**
   ```bash
   python seed.py
   ```

7. **Run the application**
   ```bash
   flask run
   # Or
   python run.py
   ```

8. **Open your browser**
   Navigate to `http://localhost:5000`

## Project Structure

```
blood_bowl_league_tracker/
├── app/
│   ├── __init__.py           # App factory
│   ├── config.py             # Configuration
│   ├── extensions.py         # Flask extensions
│   ├── models/               # Database models
│   │   ├── user.py          # User/authentication
│   │   ├── team.py          # Team, Race, Position
│   │   ├── player.py        # Player, Skills, Injuries
│   │   ├── league.py        # League, Season, Standings
│   │   └── match.py         # Match, MatchPlayerStats
│   ├── blueprints/          # Route handlers
│   │   ├── auth.py          # Authentication
│   │   ├── teams.py         # Team management
│   │   ├── leagues.py       # League management
│   │   ├── matches.py       # Match recording
│   │   └── api/             # REST API
│   ├── forms/               # WTForms
│   ├── services/            # Business logic
│   │   ├── scheduler.py     # Schedule generation
│   │   └── seed_data.py     # Database seeding
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, images
├── migrations/              # Database migrations
├── tests/                   # Test suite
├── pyproject.toml          # Project dependencies
├── seed.py                 # Database seeder
└── run.py                  # Application entry point
```

## Available Races

The following Blood Bowl races are available:

- **Tier 1**: Human, Orc, Dwarf, Skaven, Elf Union, Dark Elf, Undead, Chaos Chosen, Lizardmen
- **Tier 2**: Wood Elf

Each race has unique positions with different stats, costs, and skill access.

## API Endpoints

The application provides a REST API at `/api/`:

- `GET /api/health` - Health check
- `GET /api/teams` - List all teams
- `GET /api/teams/<id>` - Get team details
- `GET /api/races` - List all races
- `GET /api/races/<id>/positions` - Get positions for a race
- `GET /api/leagues` - List all leagues
- `GET /api/leagues/<id>` - Get league details
- `GET /api/leagues/<id>/standings` - Get league standings
- `GET /api/matches` - List all matches
- `GET /api/matches/<id>` - Get match details

## Usage

### Creating a Team

1. Register an account and log in
2. Navigate to Teams → Create Team
3. Select a race and give your team a name
4. Hire players from available positions
5. Purchase re-rolls, apothecary, and other staff

### Running a League

1. Create a new league with your desired settings
2. Invite coaches to register their teams
3. Approve registrations as commissioner
4. Generate the schedule when ready
5. Coaches record match results
6. Standings update automatically

### Recording a Match

1. Navigate to the match from your dashboard or league page
2. Enter the final score and casualties
3. Record individual player statistics
4. Save to update standings and player SPP

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## License

This is a fan-made project. Blood Bowl is a trademark of Games Workshop Ltd.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

