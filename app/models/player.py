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
    category = db.Column(db.String(20), nullable=False)  # A, S, G, M, P, E
    skill_type = db.Column(db.String(20), default="active")  # active, passive
    is_mandatory = db.Column(db.Boolean, default=False)  # Must use when applicable (marked with *)
    description = db.Column(db.Text)
    
    def __repr__(self) -> str:
        return f"<Skill {self.name}>"
    
    @property
    def category_name(self) -> str:
        """Return full category name (English)."""
        categories = {
            'A': 'Agility',
            'S': 'Strength', 
            'G': 'General',
            'M': 'Mutation',
            'P': 'Passing',
            'E': 'Extraordinary'
        }
        return categories.get(self.category, self.category)


class Trait(db.Model):
    """Blood Bowl trait (innate abilities that cannot be learned)."""
    __tablename__ = "traits"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    trait_type = db.Column(db.String(20), default="passive")  # active, passive
    is_mandatory = db.Column(db.Boolean, default=False)  # Must use when applicable (marked with *)
    description = db.Column(db.Text)
    
    def __repr__(self) -> str:
        return f"<Trait {self.name}>"


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


class PlayerTrait(db.Model):
    """Association between players and traits."""
    __tablename__ = "player_traits"
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    trait_id = db.Column(db.Integer, db.ForeignKey("traits.id"), nullable=False)
    is_starting = db.Column(db.Boolean, default=True)  # Traits usually come with position
    
    # Relationships
    trait = db.relationship("Trait", backref="player_traits")
    
    def __repr__(self) -> str:
        return f"<PlayerTrait {self.trait.name}>"


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
    
    # Stat modifiers (deltas from base position stats)
    # Positive = improvement, Negative = injury/reduction
    movement_mod = db.Column(db.Integer, default=0)
    strength_mod = db.Column(db.Integer, default=0)
    agility_mod = db.Column(db.Integer, default=0)
    passing_mod = db.Column(db.Integer, default=0)
    armor_mod = db.Column(db.Integer, default=0)
    
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
    
    # Notes
    notes = db.Column(db.Text)
    
    # Metadata
    hired_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skills = db.relationship("PlayerSkill", backref="player", lazy="dynamic", cascade="all, delete-orphan")
    traits = db.relationship("PlayerTrait", backref="player", lazy="dynamic", cascade="all, delete-orphan")
    injuries = db.relationship("Injury", backref="player", lazy="dynamic", cascade="all, delete-orphan")
    match_stats = db.relationship("MatchPlayerStats", backref="player", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Player {self.name} ({self.position.name})>"
    
    # Computed stat properties (base + modifier)
    @property
    def movement(self) -> int:
        """Get effective movement (base + modifier)."""
        return (self.position.movement if self.position else 0) + (self.movement_mod or 0)
    
    @property
    def strength(self) -> int:
        """Get effective strength (base + modifier)."""
        return (self.position.strength if self.position else 0) + (self.strength_mod or 0)
    
    @property
    def agility(self) -> int:
        """Get effective agility (base + modifier)."""
        return (self.position.agility if self.position else 0) + (self.agility_mod or 0)
    
    @property
    def passing(self) -> int:
        """Get effective passing (base + modifier)."""
        base = self.position.passing if self.position else None
        if base is None:
            return None
        return base + (self.passing_mod or 0)
    
    @property
    def armor(self) -> int:
        """Get effective armor (base + modifier)."""
        return (self.position.armor if self.position else 0) + (self.armor_mod or 0)
    
    def initialize_from_position(self) -> None:
        """Initialize player with zero modifiers (stats come from position)."""
        self.movement_mod = 0
        self.strength_mod = 0
        self.agility_mod = 0
        self.passing_mod = 0
        self.armor_mod = 0
        self.value = self.position.cost
    
    # Premium skills that add 30,000g instead of 20,000g to player value
    PREMIUM_SKILLS = {'Dodge', 'Mighty Blow', 'Block', 'Guard'}
    
    def calculate_value(self) -> int:
        """Calculate player's current value including skills and stat changes.
        
        Learned skills add to player value:
        - Premium skills (Dodge, Mighty Blow, Block, Guard): 30,000g each
        - Other skills: 20,000g each
        """
        base_value = self.position.cost
        
        # Add value for learned skills (not starting skills)
        for player_skill in self.skills.filter_by(is_starting=False).all():
            skill_name = player_skill.skill.name if player_skill.skill else ''
            if skill_name in self.PREMIUM_SKILLS:
                base_value += 30000
            else:
                base_value += 20000
        
        # Add value for stat increases (positive modifiers only)
        if (self.movement_mod or 0) > 0:
            base_value += 10000 * self.movement_mod
        if (self.strength_mod or 0) > 0:
            base_value += 20000 * self.strength_mod
        if (self.agility_mod or 0) > 0:
            base_value += 20000 * self.agility_mod
        if (self.armor_mod or 0) > 0:
            base_value += 10000 * self.armor_mod
        
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
    
    def get_trait_list(self) -> list:
        """Return list of trait names."""
        return [pt.trait.name for pt in self.traits.all()]
    
    def get_all_abilities(self) -> dict:
        """Return all skills and traits."""
        return {
            'skills': self.get_skill_list(),
            'traits': self.get_trait_list()
        }
    
    def add_skill(self, skill: 'Skill', is_starting: bool = False) -> 'PlayerSkill':
        """Add a skill to this player."""
        from app.extensions import db
        player_skill = PlayerSkill(
            player_id=self.id,
            skill_id=skill.id,
            is_starting=is_starting
        )
        db.session.add(player_skill)
        return player_skill
    
    def add_trait(self, trait: 'Trait', is_starting: bool = True) -> 'PlayerTrait':
        """Add a trait to this player."""
        from app.extensions import db
        player_trait = PlayerTrait(
            player_id=self.id,
            trait_id=trait.id,
            is_starting=is_starting
        )
        db.session.add(player_trait)
        return player_trait
    
    def assign_starting_skills(self) -> tuple:
        """
        Assign starting skills and traits from position to this player.
        Returns tuple of (skills_added, traits_added) counts.
        """
        from app.extensions import db
        
        skills_added = 0
        traits_added = 0
        
        if not self.position or not self.position.starting_skills:
            return skills_added, traits_added
        
        # Parse starting skills from position (comma-separated string)
        skill_names = [s.strip() for s in self.position.starting_skills.split(',') if s.strip()]
        
        for skill_name in skill_names:
            # Check if player already has this skill/trait
            existing_skill = self.skills.join(Skill).filter(Skill.name == skill_name).first()
            if existing_skill:
                continue
            
            existing_trait = self.traits.join(Trait).filter(Trait.name == skill_name).first()
            if existing_trait:
                continue
            
            # Try to find as a skill first
            skill = Skill.query.filter_by(name=skill_name).first()
            if skill:
                player_skill = PlayerSkill(
                    player_id=self.id,
                    skill_id=skill.id,
                    is_starting=True
                )
                db.session.add(player_skill)
                skills_added += 1
                continue
            
            # Try to find as a trait
            trait = Trait.query.filter_by(name=skill_name).first()
            if trait:
                player_trait = PlayerTrait(
                    player_id=self.id,
                    trait_id=trait.id,
                    is_starting=True
                )
                db.session.add(player_trait)
                traits_added += 1
                continue
            
            # Handle parameterized traits like "Loner (4+)" -> "Loner (X+)"
            # and "Animosity (All)" -> "Animosity"
            base_name = skill_name.split('(')[0].strip()
            
            # Check for parameterized trait
            parameterized_trait = Trait.query.filter(
                Trait.name.like(f"{base_name} (%)") | (Trait.name == base_name)
            ).first()
            if parameterized_trait:
                # Check if already has this trait
                existing = self.traits.filter_by(trait_id=parameterized_trait.id).first()
                if not existing:
                    player_trait = PlayerTrait(
                        player_id=self.id,
                        trait_id=parameterized_trait.id,
                        is_starting=True
                    )
                    db.session.add(player_trait)
                    traits_added += 1
                continue
            
            # Check for parameterized skill
            parameterized_skill = Skill.query.filter(
                Skill.name.like(f"{base_name} (%)") | (Skill.name == base_name)
            ).first()
            if parameterized_skill:
                existing = self.skills.filter_by(skill_id=parameterized_skill.id).first()
                if not existing:
                    player_skill = PlayerSkill(
                        player_id=self.id,
                        skill_id=parameterized_skill.id,
                        is_starting=True
                    )
                    db.session.add(player_skill)
                    skills_added += 1
                continue
            
            # Skill/trait not found - log warning
            import logging
            logging.warning(f"Skill/trait '{skill_name}' not found for player {self.name}")
        
        return skills_added, traits_added

