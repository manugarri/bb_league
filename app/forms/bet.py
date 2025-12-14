"""Betting forms."""
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, RadioField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length
from app.models.bet import MAX_BET_AMOUNT


class PlaceBetForm(FlaskForm):
    """Form for placing a bet on a match."""
    bet_type = RadioField(
        "Bet Type",
        choices=[
            ("win", "Team Wins (2x payout)"),
            ("touchdowns", "Exact Touchdowns (5x payout)"),
            ("injuries", "Exact Casualties (7x payout)")
        ],
        validators=[DataRequired()]
    )
    team_id = SelectField(
        "Team",
        coerce=int,
        validators=[DataRequired()]
    )
    target_value = IntegerField(
        "Predicted Value",
        validators=[NumberRange(min=0, max=20)],
        default=0
    )
    amount = IntegerField(
        "Bet Amount",
        validators=[DataRequired(), NumberRange(min=1000, max=MAX_BET_AMOUNT)],
        default=10000
    )


class AIBetForm(FlaskForm):
    """Form for creating an AI-powered bet."""
    match_id = SelectField(
        "Match",
        coerce=int,
        validators=[DataRequired()]
    )
    bet_description = TextAreaField(
        "Bet Description",
        validators=[DataRequired(), Length(min=10, max=500)],
        render_kw={"rows": 3, "placeholder": "Describe your bet prediction, e.g., 'The Orc team will score at least 2 touchdowns and cause 3 casualties'"}
    )
    amount = IntegerField(
        "Bet Amount",
        validators=[DataRequired(), NumberRange(min=1000, max=MAX_BET_AMOUNT)],
        default=10000
    )


class AIBetConfirmForm(FlaskForm):
    """Form for confirming an AI bet after seeing the multiplier."""
    ai_bet_data = HiddenField(validators=[DataRequired()])
    confirm = HiddenField(default="yes")

