# Blood Bowl League & Tournament Tracker - Product Requirements Document (PRD)

## 1. Project Overview

### 1.1 Purpose
A web application to manage Blood Bowl leagues and tournaments, enabling coaches to track their teams, record match results, view standings, and analyze player/team statistics. The application serves as a central hub for Blood Bowl communities to organize competitive play.

### 1.2 Target Users
- **Coaches**: Players who manage Blood Bowl teams
- **League Commissioners**: Administrators who run leagues and tournaments
- **Spectators**: Community members who want to follow league progress

### 1.3 Problem Statement
Blood Bowl communities often rely on spreadsheets or paper records to track league progress, leading to:
- Inconsistent record-keeping
- Difficulty calculating standings and statistics
- No centralized place for match history
- Manual calculation of player progression and injuries

---

## 2. User Stories

### 2.1 Coach Stories
- **US-001**: As a coach, I want to create and manage my team roster so I can track my players and their progression
- **US-002**: As a coach, I want to record match results including touchdowns, casualties, and MVP so my statistics are updated
- **US-003**: As a coach, I want to view my team's match history so I can review past performance
- **US-004**: As a coach, I want to apply SPP (Star Player Points) to my players so they can level up with new skills
- **US-005**: As a coach, I want to manage player injuries and deaths so my roster stays accurate
- **US-006**: As a coach, I want to hire new players and staff (apothecary, cheerleaders, etc.) using my treasury
- **US-007**: As a coach, I want to see my upcoming scheduled matches so I can plan accordingly

### 2.2 Commissioner Stories
- **US-101**: As a commissioner, I want to create a new league/tournament with custom settings (format, rules, team value limits)
- **US-102**: As a commissioner, I want to invite coaches to join my league so we can start competition
- **US-103**: As a commissioner, I want to generate match schedules (round-robin, knockout, Swiss) so coaches know who they play
- **US-104**: As a commissioner, I want to validate and approve match results to prevent errors or cheating
- **US-105**: As a commissioner, I want to manage league phases (registration, regular season, playoffs) so the competition progresses smoothly
- **US-106**: As a commissioner, I want to configure house rules and league-specific settings

### 2.3 Spectator/General Stories
- **US-201**: As a user, I want to view league standings sorted by wins/points so I can see who's leading
- **US-202**: As a user, I want to view detailed team and player statistics (most TDs, most casualties, etc.)
- **US-203**: As a user, I want to search and filter teams/players by various criteria
- **US-204**: As a user, I want to view a history of all matches with detailed box scores
- **US-205**: As a user, I want to register an account to participate in leagues

---

## 3. Key Features

### 3.1 Team Management
- Create teams selecting from official Blood Bowl races/rosters
- Manage player roster (hire, fire, rename players)
- Track player statistics (SPP, skills, injuries, niggles)
- Manage team treasury and team value (TV)
- Purchase inducements and staff
- Player progression and skill selection on level-up

Example team roster: @https://tourplay.net/es/blood-bowl/teams


### 3.2 League & Tournament Management
- **League Formats**:
  - Round-robin leagues
  - Swiss-system tournaments
  - Single/Double elimination brackets
  - Custom point systems
- **League Lifecycle**:
  - Registration phase with team approval
  - Schedule generation
  - Active season with match recording
  - Playoffs/finals
  - Season archive and history
- **Standings Board**: Visual standings table with sortable columns
- **Scheduling**: Automatic and manual match scheduling with round deadlines

Example documentation for a League management: @https://tourplay.net/es/support/content/(supportContent:manage-championships/team-championships)
and @https://tourplay.net/es/support/content/(supportContent:manage-championships/quick-guide)

### 3.3 Match Recording
- Record final score (touchdowns)
- Track individual player performance:
  - Completions, rushing yards, receiving yards
  - Casualties inflicted/sustained
  - Interceptions
  - MVP selection
- Post-match sequence:
  - Fan factor changes
  - Winnings calculation
  - Injury rolls and player deaths
  - SPP distribution

### 3.4 Statistics & Analytics
- **Leaderboards**:
  - Top scorers (TDs)
  - Most casualties inflicted
  - Most valuable players
  - Best passers
- **Team Statistics**: Win/loss record, total TDs, total casualties
- **Historical Data**: Season-over-season comparisons

### 3.5 Dashboard & Visualization
- Coach dashboard with team overview and upcoming matches
- League dashboard with standings and recent results
- Visual bracket display for knockout tournaments
- Match timeline/activity feed

### 3.6 Search & Filter
- Search teams by name, race, coach
- Filter players by skills, position, statistics
- Filter matches by date, teams involved, league

### 3.7 User & Authentication
- User registration and login
- Role-based access (coach, commissioner, admin)
- Profile management

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Page load time < 2 seconds for standard views
- Support for at least 50 concurrent users
- Database queries optimized with proper indexing

### 4.2 Responsiveness
- Mobile-first responsive design
- Fully functional on tablets and smartphones
- Minimum supported viewport: 320px width

### 4.3 Security
- Secure password hashing (bcrypt)
- JWT-based authentication
- Input validation and SQL injection prevention
- CSRF protection on all forms

### 4.4 Usability
- Intuitive navigation with clear information hierarchy
- Consistent UI patterns across all pages
- Form validation with helpful error messages
- Accessibility compliance (WCAG 2.1 AA)

### 4.5 Data Integrity
- Transactional database operations for match recording
- Audit trail for commissioner actions
- Data backup capabilities

### 4.6 Scalability
- Modular architecture supporting future features
- Database schema designed for growth

---

## 5. Tech Stack

### 5.1 Backend
- **Framework**: Flask (Python 3.11+)
- **ORM**: Flask-SQLAlchemy
- **Database**: SQLite (development) / PostgreSQL (production)
- **Migrations**: Flask-Migrate (Alembic)
- **Authentication**: Flask-JWT-Extended
- **Serialization**: Marshmallow
- **API Style**: RESTful with Flask Blueprints

### 5.2 Frontend
- **Templating**: Jinja2
- **CSS Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS (minimal dependencies)
- **Icons**: Bootstrap Icons or Font Awesome

### 5.3 Development & Deployment
- **Testing**: pytest
- **Server**: Gunicorn (production)
- **Environment**: python-dotenv for configuration
- **Version Control**: Git
- **Package Management**: uv
---

## 6. Data Model (Core Entities)

### 6.1 Primary Entities
- **User**: Account information, authentication
- **Coach**: Profile linked to user, team ownership
- **Team**: Roster, treasury, statistics, race
- **Player**: Stats, skills, injuries, position
- **League**: Settings, format, participating teams
- **Match**: Teams, scores, date, league reference
- **MatchPlayerStats**: Individual performance per match

### 6.2 Supporting Entities
- **Race**: Blood Bowl races with available positions
- **Position**: Player positions with base stats
- **Skill**: Available skills and their effects
- **Season**: Historical league seasons

---

## 7. MVP Scope (Phase 1)

### Must Have
- [ ] User registration and authentication
- [ ] Team creation with race selection
- [ ] Player roster management
- [ ] League creation with basic settings
- [ ] Round-robin schedule generation
- [ ] Match result recording
- [ ] Standings calculation and display
- [ ] Basic team/player statistics

### Should Have
- [ ] Player skill progression
- [ ] Injury tracking
- [ ] Commissioner approval workflow
- [ ] Search and filter functionality

### Could Have
- [ ] Knockout tournament brackets
- [ ] Advanced statistics and charts
- [ ] Match timeline/play-by-play
- [ ] Export data to PDF/CSV

### Won't Have (Future)
- [ ] Real-time match tracking
- [ ] Mobile native apps
- [ ] Integration with tabletop simulators
- [ ] Automated matchmaking

---

## 8. Project Structure

```
blood_bowl_league_tracker/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Configuration
│   ├── extensions.py            # Flask extensions
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── team.py
│   │   ├── player.py
│   │   ├── league.py
│   │   └── match.py
│   ├── blueprints/              # Route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── teams.py
│   │   ├── leagues.py
│   │   ├── matches.py
│   │   └── api/
│   ├── schemas/                 # Marshmallow schemas
│   ├── services/                # Business logic
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── teams/
│   │   ├── leagues/
│   │   └── matches/
│   └── static/                  # CSS, JS, images
│       ├── css/
│       ├── js/
│       └── img/
├── migrations/                  # Database migrations
├── tests/                       # Test suite
├── requirements.txt
├── .env.example
└── run.py                       # Application entry point
```

---

*Document Version: 1.0*  
*Last Updated: December 2025*
