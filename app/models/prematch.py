"""Pre-match activity models including inducements."""
import json
from datetime import datetime
from typing import Optional
from app.extensions import db


class MatchInducement(db.Model):
    """Inducement purchased by a team for a specific match."""
    __tablename__ = "match_inducements"
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Inducement details
    inducement_id = db.Column(db.String(64), nullable=False)  # References inducements.json id
    inducement_name = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    cost_per_unit = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Integer, nullable=False)
    
    # For star players and mercenaries - store additional data as JSON
    extra_data = db.Column(db.Text)  # JSON: star_player_id, mercenary_position_id, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    match = db.relationship("Match", backref=db.backref("inducements", lazy="dynamic", cascade="all, delete-orphan"))
    team = db.relationship("Team", backref=db.backref("match_inducements", lazy="dynamic"))
    
    def __repr__(self) -> str:
        return f"<MatchInducement {self.inducement_name} x{self.quantity} for team {self.team_id}>"
    
    def get_extra_data(self) -> dict:
        """Parse extra_data JSON."""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_extra_data(self, data: dict) -> None:
        """Set extra_data as JSON."""
        self.extra_data = json.dumps(data) if data else None


class PreMatchSubmission(db.Model):
    """Tracks pre-match activity submissions for each team in a match."""
    __tablename__ = "prematch_submissions"
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    
    # Submission status
    inducements_submitted = db.Column(db.Boolean, default=False)
    inducements_submitted_at = db.Column(db.DateTime)
    
    # Total gold spent on inducements
    total_inducements_cost = db.Column(db.Integer, default=0)
    
    # Notes from the coach
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    match = db.relationship("Match", backref=db.backref("prematch_submissions", lazy="dynamic", cascade="all, delete-orphan"))
    team = db.relationship("Team", backref=db.backref("prematch_submissions", lazy="dynamic"))
    
    # Unique constraint: one submission per team per match
    __table_args__ = (
        db.UniqueConstraint('match_id', 'team_id', name='unique_prematch_submission'),
    )
    
    def __repr__(self) -> str:
        return f"<PreMatchSubmission match={self.match_id} team={self.team_id}>"
    
    @property
    def is_complete(self) -> bool:
        """Check if all pre-match activities have been submitted."""
        return self.inducements_submitted
    
    def submit_inducements(self) -> None:
        """Mark inducements as submitted."""
        self.inducements_submitted = True
        self.inducements_submitted_at = datetime.utcnow()


def get_inducements_data() -> dict:
    """Load inducements data from JSON file."""
    import os
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'inducements.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"inducements": [], "prayers_to_nuffle": []}


def get_available_inducements(team, match=None) -> list:
    """
    Get list of inducements available to a team based on their race and special rules.
    
    Args:
        team: The Team object
        match: Optional Match object (for checking league rules)
    
    Returns:
        List of available inducement definitions with costs adjusted for discounts
    """
    data = get_inducements_data()
    inducements = data.get("inducements", [])
    race = team.race
    
    # Get team's special rules
    special_rules = [rule.get("name", "") for rule in race.get_special_rules()]
    race_name = race.name
    
    # Check if team can hire apothecaries
    can_hire_apothecary = race.apothecary_allowed
    
    # Check league rules for star players (if in a league match)
    allow_star_players = True
    if match and match.league:
        allow_star_players = match.league.allow_star_players
    
    available = []
    
    for ind in inducements:
        ind_copy = ind.copy()
        
        # Check availability
        availability = ind.get("available_to", "all")
        
        if availability == "special_rule":
            # Requires specific special rule(s)
            required_rules = ind.get("special_rules_required", [])
            if not any(rule in special_rules for rule in required_rules):
                continue
        
        elif availability == "apothecary_allowed":
            # Only for teams that can hire apothecaries
            if not can_hire_apothecary:
                continue
        
        elif availability == "star_players_allowed":
            # Only if league allows star players
            if not allow_star_players:
                continue
        
        # Check excluded special rules
        excluded_rules = ind.get("special_rules_excluded", [])
        if any(rule in special_rules for rule in excluded_rules):
            continue
        
        # Apply race/special rule discounts
        race_discounts = ind.get("race_discount", {})
        discounted_cost = ind.get("cost", 0)
        
        # Check if race name matches
        if race_name in race_discounts:
            discounted_cost = race_discounts[race_name]
        
        # Check if any special rule matches for discount
        for rule in special_rules:
            if rule in race_discounts:
                discounted_cost = race_discounts[rule]
                break
        
        ind_copy["original_cost"] = ind.get("cost", 0)
        ind_copy["cost"] = discounted_cost
        ind_copy["has_discount"] = discounted_cost < ind.get("cost", 0)
        
        # Adjust max quantity based on special rules
        max_qty_rules = ind.get("max_quantity_with_rule", {})
        for rule, max_qty in max_qty_rules.items():
            if rule in special_rules:
                ind_copy["max_quantity"] = max_qty
                break
        
        available.append(ind_copy)
    
    return available


def calculate_petty_cash(home_team, away_team) -> tuple:
    """
    Calculate petty cash for inducements based on team value difference.
    
    The team with lower TV receives gold equal to the difference.
    
    Args:
        home_team: Home Team object
        away_team: Away Team object
    
    Returns:
        Tuple of (home_petty_cash, away_petty_cash)
    """
    home_tv = home_team.calculate_tv()
    away_tv = away_team.calculate_tv()
    
    diff = abs(home_tv - away_tv)
    
    if home_tv < away_tv:
        return (diff, 0)
    elif away_tv < home_tv:
        return (0, diff)
    else:
        return (0, 0)

