"""Team and race models."""
from datetime import datetime
from app.extensions import db


# Association table for teams and their hired star players
team_star_players = db.Table(
    'team_star_players',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('star_player_id', db.Integer, db.ForeignKey('star_players.id'), primary_key=True),
    db.Column('hired_at', db.DateTime, default=datetime.utcnow)
)


class Race(db.Model):
    """Blood Bowl race/roster."""
    __tablename__ = "races"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    reroll_cost = db.Column(db.Integer, default=60000)
    apothecary_allowed = db.Column(db.Boolean, default=True)
    special_rules = db.Column(db.Text)  # JSON array of special rules
    tier = db.Column(db.Integer, default=1)  # 1-3 tier rating
    
    # Relationships
    positions = db.relationship("Position", backref="race", lazy="dynamic")
    teams = db.relationship("Team", backref="race", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Race {self.name}>"


class Position(db.Model):
    """Player position within a race."""
    __tablename__ = "positions"
    
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey("races.id"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    
    # Base stats
    movement = db.Column(db.Integer, default=6)
    strength = db.Column(db.Integer, default=3)
    agility = db.Column(db.Integer, default=3)
    passing = db.Column(db.Integer, default=3)
    armor = db.Column(db.Integer, default=8)
    
    # Position limits
    max_count = db.Column(db.Integer, default=16)
    min_count = db.Column(db.Integer, default=0)
    cost = db.Column(db.Integer, default=50000)
    
    # Starting skills (JSON array)
    starting_skills = db.Column(db.Text)
    # Primary skill access (JSON array of skill categories)
    primary_skills = db.Column(db.Text)
    # Secondary skill access
    secondary_skills = db.Column(db.Text)
    
    # Relationships
    players = db.relationship("Player", backref="position", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Position {self.name} ({self.race.name})>"


class Team(db.Model):
    """Blood Bowl team."""
    __tablename__ = "teams"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey("races.id"), nullable=False)
    
    # Team resources
    treasury = db.Column(db.Integer, default=1000000)
    rerolls = db.Column(db.Integer, default=0)
    fan_factor = db.Column(db.Integer, default=1)
    assistant_coaches = db.Column(db.Integer, default=0)
    cheerleaders = db.Column(db.Integer, default=0)
    has_apothecary = db.Column(db.Boolean, default=False)
    
    # Team value
    current_tv = db.Column(db.Integer, default=0)
    
    # Statistics
    games_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    touchdowns_for = db.Column(db.Integer, default=0)
    touchdowns_against = db.Column(db.Integer, default=0)
    casualties_inflicted = db.Column(db.Integer, default=0)
    casualties_suffered = db.Column(db.Integer, default=0)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    players = db.relationship("Player", backref="team", lazy="dynamic", cascade="all, delete-orphan")
    staff = db.relationship("TeamStaff", backref="team", lazy="dynamic", cascade="all, delete-orphan")
    star_players = db.relationship("StarPlayer", secondary=team_star_players, backref=db.backref("teams", lazy="dynamic"))
    league_entries = db.relationship("LeagueTeam", backref="team", lazy="dynamic", cascade="all, delete-orphan")
    home_matches = db.relationship("Match", foreign_keys="Match.home_team_id", backref="home_team", lazy="dynamic", cascade="all, delete-orphan")
    away_matches = db.relationship("Match", foreign_keys="Match.away_team_id", backref="away_team", lazy="dynamic", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Team {self.name}>"
    
    def calculate_tv(self) -> int:
        """Calculate current team value."""
        tv = 0
        
        # Player values
        for player in self.players.filter_by(is_active=True):
            tv += player.calculate_value()
        
        # Star player values
        for star in self.star_players:
            tv += star.cost
        
        # Team assets
        tv += self.rerolls * self.race.reroll_cost
        tv += self.assistant_coaches * 10000
        tv += self.cheerleaders * 10000
        if self.has_apothecary:
            tv += 50000
        
        self.current_tv = tv
        return tv
    
    @property
    def active_players(self):
        """Return active (non-dead) players."""
        return self.players.filter_by(is_active=True)
    
    @property
    def roster_count(self) -> int:
        """Return number of active players."""
        return self.active_players.count()
    
    def get_record_string(self) -> str:
        """Return win-draw-loss record string."""
        return f"{self.wins}-{self.draws}-{self.losses}"


class TeamStaff(db.Model):
    """Team staff members (special hires)."""
    __tablename__ = "team_staff"
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    staff_type = db.Column(db.String(32), nullable=False)  # apothecary, coach, cheerleader, etc.
    name = db.Column(db.String(64))
    cost = db.Column(db.Integer, default=0)
    hired_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<TeamStaff {self.staff_type} for {self.team.name}>"


class TeamStarPlayer(db.Model):
    """Association between teams and star players they have hired."""
    __tablename__ = "team_star_player_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    star_player_id = db.Column(db.Integer, db.ForeignKey("star_players.id"), nullable=False)
    hired_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    team = db.relationship("Team", backref=db.backref("star_player_entries", lazy="dynamic"))
    star_player = db.relationship("StarPlayer", backref=db.backref("team_entries", lazy="dynamic"))
    
    def __repr__(self) -> str:
        return f"<TeamStarPlayer {self.star_player.name} for team {self.team.name}>"

