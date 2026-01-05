"""League forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, BooleanField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional


class CreateLeagueForm(FlaskForm):
    """Create league form."""
    name = StringField(
        "League Name",
        validators=[DataRequired(), Length(min=3, max=128)]
    )
    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=2000)]
    )
    format = SelectField(
        "Format",
        choices=[
            ("round_robin", "Round Robin"),
            ("swiss", "Swiss System"),
            ("knockout", "Knockout"),
            ("custom", "Custom")
        ],
        validators=[DataRequired()]
    )
    max_teams = IntegerField(
        "Maximum Teams",
        default=8,
        validators=[InputRequired(), NumberRange(min=2, max=32)]
    )
    min_teams = IntegerField(
        "Minimum Teams",
        default=4,
        validators=[InputRequired(), NumberRange(min=2, max=32)]
    )
    starting_treasury = IntegerField(
        "Starting Treasury",
        default=1000000,
        validators=[InputRequired(), NumberRange(min=0)]
    )
    win_points = IntegerField(
        "Points for Win",
        default=3,
        validators=[InputRequired(), NumberRange(min=0, max=10)]
    )
    draw_points = IntegerField(
        "Points for Draw",
        default=1,
        validators=[InputRequired(), NumberRange(min=0, max=10)]
    )
    loss_points = IntegerField(
        "Points for Loss",
        default=0,
        validators=[InputRequired(), NumberRange(min=0, max=10)]
    )
    min_roster_size = IntegerField(
        "Minimum Roster Size",
        default=11,
        validators=[InputRequired(), NumberRange(min=1, max=16)]
    )
    max_roster_size = IntegerField(
        "Maximum Roster Size",
        default=16,
        validators=[InputRequired(), NumberRange(min=1, max=20)]
    )
    allow_star_players = BooleanField(
        "Allow Star Players",
        default=True
    )
    is_public = BooleanField(
        "Public League",
        default=True
    )


class EditLeagueForm(FlaskForm):
    """Edit league form."""
    name = StringField(
        "League Name",
        validators=[DataRequired(), Length(min=3, max=128)]
    )
    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=2000)]
    )
    max_teams = IntegerField(
        "Maximum Teams",
        validators=[DataRequired(), NumberRange(min=2, max=32)]
    )
    min_roster_size = IntegerField(
        "Minimum Roster Size",
        validators=[InputRequired(), NumberRange(min=1, max=16)]
    )
    max_roster_size = IntegerField(
        "Maximum Roster Size",
        validators=[InputRequired(), NumberRange(min=1, max=20)]
    )
    allow_star_players = BooleanField("Allow Star Players")
    is_public = BooleanField("Public League")
    registration_open = BooleanField("Registration Open")


class JoinLeagueForm(FlaskForm):
    """Join league form."""
    team_id = SelectField(
        "Team",
        coerce=int,
        validators=[DataRequired()]
    )


class ScheduleMatchForm(FlaskForm):
    """Schedule a new match form (admin only)."""
    home_team_id = SelectField(
        "Home Team",
        coerce=int,
        validators=[DataRequired()]
    )
    away_team_id = SelectField(
        "Away Team",
        coerce=int,
        validators=[DataRequired()]
    )
    round_number = IntegerField(
        "Round Number",
        default=1,
        validators=[InputRequired(), NumberRange(min=1, max=50)]
    )
