"""Player and skill models."""
from datetime import datetime
from app.extensions import db


# Association table for star players and races they can play for
star_player_races = db.Table(
    'star_player_races',
    db.Column('star_player_id', db.Integer, db.ForeignKey('star_players.id'), primary_key=True),
    db.Column('race_id', db.Integer, db.ForeignKey('races.id'), primary_key=True)
)


class StarPlayer(db.Model):
    """Blood Bowl Star Player that can be hired for a match."""
    __tablename__ = "star_players"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    
    # Stats
    movement = db.Column(db.Integer, nullable=False)
    strength = db.Column(db.Integer, nullable=False)
    agility = db.Column(db.Integer, nullable=False)
    passing = db.Column(db.Integer)  # Can be null for some players
    armor = db.Column(db.Integer, nullable=False)
    
    # Skills and abilities
    skills = db.Column(db.Text)  # Comma-separated list
    special_abilities = db.Column(db.Text)  # JSON array or comma-separated
    
    # Relationships
    available_to_races = db.relationship('Race', secondary=star_player_races, 
                                         backref=db.backref('star_players', lazy='dynamic'))
    
    def __repr__(self) -> str:
        return f"<StarPlayer {self.name}>"
    
    def get_skill_list(self) -> list:
        """Return list of skill names."""
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',')]
    
    def get_special_abilities(self) -> list:
        """Return list of special abilities."""
        if not self.special_abilities:
            return []
        return [s.strip() for s in self.special_abilities.split('|')]


class Skill(db.Model):
    """Blood Bowl skill."""
    __tablename__ = "skills"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # General, Agility, Strength, Passing, Mutation
    description = db.Column(db.Text)
    
    def __repr__(self) -> str:
        return f"<Skill {self.name}>"


class PlayerSkill(db.Model):
    """Association between players and skills."""
    __tablename__ = "player_skills"
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False)
    is_starting = db.Column(db.Boolean, default=False)  # True if came with position
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    skill = db.relationship("Skill", backref="player_skills")
    
    def __repr__(self) -> str:
        return f"<PlayerSkill {self.skill.name}>"


class Injury(db.Model):
    """Player injury record."""
    __tablename__ = "injuries"
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    injury_type = db.Column(db.String(32), nullable=False)  # Miss Next Game, Niggling, -MA, -AV, etc.
    description = db.Column(db.String(128))
    is_permanent = db.Column(db.Boolean, default=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Injury {self.injury_type}>"


class Player(db.Model):
    """Blood Bowl player."""
    __tablename__ = "players"
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey("positions.id"), nullable=False)
    
    # Player info
    name = db.Column(db.String(64), nullable=False)
    number = db.Column(db.Integer)
    
    # Current stats (can differ from position base due to injuries/improvements)
    movement = db.Column(db.Integer)
    strength = db.Column(db.Integer)
    agility = db.Column(db.Integer)
    passing = db.Column(db.Integer)
    armor = db.Column(db.Integer)
    
    # Experience
    spp = db.Column(db.Integer, default=0)  # Star Player Points
    level = db.Column(db.Integer, default=1)
    
    # Career statistics
    games_played = db.Column(db.Integer, default=0)
    touchdowns = db.Column(db.Integer, default=0)
    casualties_inflicted = db.Column(db.Integer, default=0)
    completions = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    deflections = db.Column(db.Integer, default=0)
    mvp_awards = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_dead = db.Column(db.Boolean, default=False)
    miss_next_game = db.Column(db.Boolean, default=False)
    niggling_injuries = db.Column(db.Integer, default=0)
    
    # Value
    value = db.Column(db.Integer, default=0)
    
    # Metadata
    hired_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skills = db.relationship("PlayerSkill", backref="player", lazy="dynamic", cascade="all, delete-orphan")
    injuries = db.relationship("Injury", backref="player", lazy="dynamic", cascade="all, delete-orphan")
    match_stats = db.relationship("MatchPlayerStats", backref="player", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Player {self.name} ({self.position.name})>"
    
    def initialize_from_position(self) -> None:
        """Set stats from position defaults."""
        self.movement = self.position.movement
        self.strength = self.position.strength
        self.agility = self.position.agility
        self.passing = self.position.passing
        self.armor = self.position.armor
        self.value = self.position.cost
    
    def calculate_value(self) -> int:
        """Calculate player's current value including skills."""
        base_value = self.position.cost
        
        # Add value for learned skills (not starting skills)
        learned_skills = self.skills.filter_by(is_starting=False).count()
        base_value += learned_skills * 20000
        
        # Add value for stat increases (approximation)
        if self.movement > self.position.movement:
            base_value += 10000 * (self.movement - self.position.movement)
        if self.strength > self.position.strength:
            base_value += 20000 * (self.strength - self.position.strength)
        if self.agility > self.position.agility:
            base_value += 20000 * (self.agility - self.position.agility)
        if self.armor > self.position.armor:
            base_value += 10000 * (self.armor - self.position.armor)
        
        self.value = base_value
        return base_value
    
    def add_spp(self, amount: int) -> None:
        """Add SPP and check for level up."""
        self.spp += amount
        self.check_level_up()
    
    def check_level_up(self) -> bool:
        """Check if player has enough SPP for next level."""
        spp_thresholds = [0, 6, 16, 31, 51, 76, 176]  # Levels 1-7+
        if self.level < len(spp_thresholds):
            if self.spp >= spp_thresholds[self.level]:
                return True
        return False
    
    def get_spp_breakdown(self) -> dict:
        """Return SPP earned by type."""
        return {
            "touchdowns": self.touchdowns * 3,
            "casualties": self.casualties_inflicted * 2,
            "completions": self.completions * 1,
            "interceptions": self.interceptions * 2,
            "deflections": self.deflections * 1,
            "mvps": self.mvp_awards * 4,
            "total": self.spp
        }
    
    def get_skill_list(self) -> list:
        """Return list of skill names."""
        return [ps.skill.name for ps in self.skills.all()]

