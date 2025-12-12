"""Match and match statistics models."""
from datetime import datetime
from app.extensions import db


class Match(db.Model):
    """Blood Bowl match."""
    __tablename__ = "matches"
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"))
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"))
    
    # Teams
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Scheduling
    round_number = db.Column(db.Integer)
    scheduled_date = db.Column(db.DateTime)
    played_date = db.Column(db.DateTime)
    
    # Score
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    
    # Team stats
    home_casualties = db.Column(db.Integer, default=0)
    away_casualties = db.Column(db.Integer, default=0)
    
    # Post-match
    home_winnings = db.Column(db.Integer, default=0)
    away_winnings = db.Column(db.Integer, default=0)
    home_fan_factor_change = db.Column(db.Integer, default=0)
    away_fan_factor_change = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default="scheduled")  # scheduled, in_progress, completed, cancelled
    is_validated = db.Column(db.Boolean, default=False)
    validated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    validated_at = db.Column(db.DateTime)
    
    # Match notes
    notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    player_stats = db.relationship("MatchPlayerStats", backref="match", lazy="dynamic", cascade="all, delete-orphan")
    season = db.relationship("Season", backref="matches")
    validator = db.relationship("User", foreign_keys=[validated_by])
    
    def __repr__(self) -> str:
        return f"<Match {self.home_team.name} vs {self.away_team.name}>"
    
    @property
    def is_completed(self) -> bool:
        """Check if match is completed."""
        return self.status == "completed"
    
    @property
    def winner(self):
        """Return winning team or None for draw."""
        if not self.is_completed:
            return None
        if self.home_score > self.away_score:
            return self.home_team
        elif self.away_score > self.home_score:
            return self.away_team
        return None
    
    @property
    def loser(self):
        """Return losing team or None for draw."""
        if not self.is_completed:
            return None
        if self.home_score > self.away_score:
            return self.away_team
        elif self.away_score > self.home_score:
            return self.home_team
        return None
    
    @property
    def is_draw(self) -> bool:
        """Check if match ended in a draw."""
        return self.is_completed and self.home_score == self.away_score
    
    def get_score_string(self) -> str:
        """Return formatted score string."""
        return f"{self.home_score} - {self.away_score}"
    
    def get_team_stats(self, team_id: int) -> dict:
        """Get aggregated stats for a team in this match."""
        is_home = team_id == self.home_team_id
        
        return {
            "score": self.home_score if is_home else self.away_score,
            "opponent_score": self.away_score if is_home else self.home_score,
            "casualties": self.home_casualties if is_home else self.away_casualties,
            "casualties_suffered": self.away_casualties if is_home else self.home_casualties,
            "winnings": self.home_winnings if is_home else self.away_winnings,
            "fan_factor_change": self.home_fan_factor_change if is_home else self.away_fan_factor_change,
        }


class MatchPlayerStats(db.Model):
    """Individual player performance in a match."""
    __tablename__ = "match_player_stats"
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Performance stats
    touchdowns = db.Column(db.Integer, default=0)
    completions = db.Column(db.Integer, default=0)
    passing_yards = db.Column(db.Integer, default=0)
    rushing_yards = db.Column(db.Integer, default=0)
    receiving_yards = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    deflections = db.Column(db.Integer, default=0)
    casualties_inflicted = db.Column(db.Integer, default=0)
    casualties_suffered = db.Column(db.Integer, default=0)
    
    # Special
    is_mvp = db.Column(db.Boolean, default=False)
    
    # Injury in this match
    injury_result = db.Column(db.String(32))  # None, Badly Hurt, Miss Next Game, Niggling, etc.
    was_killed = db.Column(db.Boolean, default=0)
    
    # SPP earned this match
    spp_earned = db.Column(db.Integer, default=0)
    
    # Relationships
    team = db.relationship("Team", backref="match_player_stats")
    
    def __repr__(self) -> str:
        return f"<MatchPlayerStats {self.player.name}>"
    
    def calculate_spp(self) -> int:
        """Calculate SPP earned in this match."""
        spp = 0
        spp += self.touchdowns * 3
        spp += self.casualties_inflicted * 2
        spp += self.completions * 1
        spp += self.interceptions * 2
        spp += self.deflections * 1
        if self.is_mvp:
            spp += 4
        
        self.spp_earned = spp
        return spp

