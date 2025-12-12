"""User model for authentication and authorization."""
from datetime import datetime
from typing import Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="coach")  # coach, commissioner, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile information
    display_name = db.Column(db.String(64))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(256))
    
    # Relationships
    teams = db.relationship("Team", backref="coach", lazy="dynamic")
    leagues_created = db.relationship(
        "League", 
        backref="commissioner", 
        lazy="dynamic",
        foreign_keys="League.commissioner_id"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_commissioner(self) -> bool:
        """Check if user has commissioner privileges."""
        return self.role in ("commissioner", "admin")
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == "admin"
    
    def get_display_name(self) -> str:
        """Return display name or username."""
        return self.display_name or self.username


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))

