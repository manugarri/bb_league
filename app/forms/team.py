"""Team forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CreateTeamForm(FlaskForm):
    """Create team form."""
    name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    race_id = SelectField(
        "Race",
        coerce=int,
        validators=[DataRequired()]
    )
    league_type = SelectField(
        "League Type",
        choices=[],
        validators=[Optional()]
    )
    treasury = IntegerField(
        "Treasury",
        validators=[Optional(), NumberRange(min=0, max=10000000)],
        default=1000000
    )


class EditTeamForm(FlaskForm):
    """Edit team form."""
    name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    league_type = SelectField(
        "League Type",
        choices=[],
        validators=[Optional()]
    )
    treasury = IntegerField(
        "Treasury",
        validators=[Optional(), NumberRange(min=0, max=10000000)]
    )
    # Team assets
    rerolls = IntegerField(
        "Rerolls",
        validators=[Optional(), NumberRange(min=0, max=8)]
    )
    assistant_coaches = IntegerField(
        "Assistant Coaches",
        validators=[Optional(), NumberRange(min=0, max=6)]
    )
    cheerleaders = IntegerField(
        "Cheerleaders",
        validators=[Optional(), NumberRange(min=0, max=12)]
    )
    has_apothecary = BooleanField("Apothecary")
    fan_factor = IntegerField(
        "Fan Factor",
        validators=[Optional(), NumberRange(min=0, max=20)]
    )


class HirePlayerForm(FlaskForm):
    """Hire player form."""
    name = StringField(
        "Player Name",
        validators=[DataRequired(), Length(min=1, max=64)]
    )
    position_id = SelectField(
        "Position",
        coerce=int,
        validators=[DataRequired()]
    )
    number = IntegerField(
        "Jersey Number",
        validators=[Optional(), NumberRange(min=1, max=99)]
    )


class EditPlayerForm(FlaskForm):
    """Edit player form."""
    name = StringField(
        "Player Name",
        validators=[DataRequired(), Length(min=1, max=64)]
    )
    number = IntegerField(
        "Jersey Number",
        validators=[Optional(), NumberRange(min=1, max=99)]
    )
    notes = TextAreaField(
        "Notes",
        validators=[Optional(), Length(max=1000)]
    )

