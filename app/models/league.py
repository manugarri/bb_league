"""League and season models."""
from datetime import datetime
from app.extensions import db


class League(db.Model):
    """Blood Bowl league."""
    __tablename__ = "leagues"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    commissioner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    description = db.Column(db.Text)
    
    # League settings
    format = db.Column(db.String(32), default="round_robin")  # round_robin, swiss, knockout, custom
    max_teams = db.Column(db.Integer, default=8)
    min_teams = db.Column(db.Integer, default=4)
    starting_treasury = db.Column(db.Integer, default=1000000)
    max_team_value = db.Column(db.Integer)  # Optional TV cap
    
    # Roster rules
    min_roster_size = db.Column(db.Integer, default=11)
    max_roster_size = db.Column(db.Integer, default=16)
    allow_star_players = db.Column(db.Boolean, default=True)
    
    # Scoring system
    win_points = db.Column(db.Integer, default=3)
    draw_points = db.Column(db.Integer, default=1)
    loss_points = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default="registration")  # registration, active, playoffs, completed
    registration_open = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    
    # House rules (JSON)
    house_rules = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seasons = db.relationship("Season", backref="league", lazy="dynamic", cascade="all, delete-orphan")
    teams = db.relationship("LeagueTeam", backref="league", lazy="dynamic", cascade="all, delete-orphan")
    matches = db.relationship("Match", backref="league", lazy="dynamic", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<League {self.name}>"
    
    @property
    def current_season(self):
        """Get the current active season."""
        return self.seasons.filter_by(is_active=True).first()
    
    @property
    def team_count(self) -> int:
        """Return number of registered teams."""
        return self.teams.filter_by(is_approved=True).count()
    
    def can_register(self) -> bool:
        """Check if league is open for registration."""
        if not self.registration_open:
            return False
        if self.status != "registration":
            return False
        if self.team_count >= self.max_teams:
            return False
        return True


class Season(db.Model):
    """League season."""
    __tablename__ = "seasons"
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    number = db.Column(db.Integer, default=1)
    
    # Dates
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Round information
    current_round = db.Column(db.Integer, default=1)
    total_rounds = db.Column(db.Integer)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    standings = db.relationship("Standing", backref="season", lazy="dynamic", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Season {self.name}>"


class LeagueTeam(db.Model):
    """Association between leagues and teams."""
    __tablename__ = "league_teams"
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Registration status
    is_approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    
    # Seed (for playoffs/brackets)
    seed = db.Column(db.Integer)
    
    # Registration date
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<LeagueTeam {self.team.name} in {self.league.name}>"


class Standing(db.Model):
    """League standings for a team in a season."""
    __tablename__ = "standings"
    
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Position
    rank = db.Column(db.Integer)
    
    # Record
    played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    
    # Statistics
    touchdowns_for = db.Column(db.Integer, default=0)
    touchdowns_against = db.Column(db.Integer, default=0)
    casualties_inflicted = db.Column(db.Integer, default=0)
    casualties_suffered = db.Column(db.Integer, default=0)
    
    # Relationships
    team = db.relationship("Team", backref="standings")
    
    def __repr__(self) -> str:
        return f"<Standing {self.team.name}: {self.points}pts>"
    
    @property
    def touchdown_diff(self) -> int:
        """Calculate touchdown differential."""
        return self.touchdowns_for - self.touchdowns_against
    
    @property
    def casualty_diff(self) -> int:
        """Calculate casualty differential."""
        return self.casualties_inflicted - self.casualties_suffered
    
    def update_from_match(self, is_home: bool, match) -> None:
        """Update standing based on match result."""
        self.played += 1
        
        if is_home:
            tds_for = match.home_score
            tds_against = match.away_score
            cas_for = match.home_casualties
            cas_against = match.away_casualties
        else:
            tds_for = match.away_score
            tds_against = match.home_score
            cas_for = match.away_casualties
            cas_against = match.home_casualties
        
        self.touchdowns_for += tds_for
        self.touchdowns_against += tds_against
        self.casualties_inflicted += cas_for
        self.casualties_suffered += cas_against
        
        # Determine result
        if tds_for > tds_against:
            self.wins += 1
            self.points += match.league.win_points
        elif tds_for < tds_against:
            self.losses += 1
            self.points += match.league.loss_points
        else:
            self.draws += 1
            self.points += match.league.draw_points

