"""Team forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField
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


class EditTeamForm(FlaskForm):
    """Edit team form."""
    name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=3, max=64)]
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

