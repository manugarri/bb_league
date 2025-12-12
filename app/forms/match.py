"""Match forms."""
from flask_wtf import FlaskForm
from wtforms import IntegerField, TextAreaField, SelectField, BooleanField
from wtforms.validators import InputRequired, NumberRange, Optional


class RecordMatchForm(FlaskForm):
    """Record match result form."""
    home_score = IntegerField(
        "Home Score",
        default=0,
        validators=[InputRequired(), NumberRange(min=0, max=20)]
    )
    away_score = IntegerField(
        "Away Score",
        default=0,
        validators=[InputRequired(), NumberRange(min=0, max=20)]
    )
    home_casualties = IntegerField(
        "Home Casualties Inflicted",
        default=0,
        validators=[InputRequired(), NumberRange(min=0, max=20)]
    )
    away_casualties = IntegerField(
        "Away Casualties Inflicted",
        default=0,
        validators=[InputRequired(), NumberRange(min=0, max=20)]
    )
    home_winnings = IntegerField(
        "Home Winnings",
        default=0,
        validators=[InputRequired(), NumberRange(min=0)]
    )
    away_winnings = IntegerField(
        "Away Winnings",
        default=0,
        validators=[InputRequired(), NumberRange(min=0)]
    )
    notes = TextAreaField(
        "Match Notes",
        validators=[Optional()]
    )


class MatchPlayerStatsForm(FlaskForm):
    """Individual player stats form."""
    touchdowns = IntegerField(
        "Touchdowns",
        default=0,
        validators=[NumberRange(min=0, max=10)]
    )
    completions = IntegerField(
        "Completions",
        default=0,
        validators=[NumberRange(min=0, max=20)]
    )
    interceptions = IntegerField(
        "Interceptions",
        default=0,
        validators=[NumberRange(min=0, max=10)]
    )
    casualties_inflicted = IntegerField(
        "Casualties",
        default=0,
        validators=[NumberRange(min=0, max=10)]
    )
    is_mvp = BooleanField("MVP")
    injury_result = SelectField(
        "Injury",
        choices=[
            ("", "None"),
            ("badly_hurt", "Badly Hurt"),
            ("miss_next_game", "Miss Next Game"),
            ("niggling", "Niggling Injury"),
            ("-1ma", "-1 MA"),
            ("-1av", "-1 AV"),
            ("-1ag", "-1 AG"),
            ("-1st", "-1 ST"),
            ("-1pa", "-1 PA"),
            ("dead", "Dead")
        ],
        validators=[Optional()]
    )

