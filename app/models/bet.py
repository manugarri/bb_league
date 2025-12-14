"""Betting models for match wagering."""
import json
import os
from datetime import datetime
from typing import Optional

from app.extensions import db


class BetType:
    """Bet type constants."""
    WIN = "win"  # Bet on team winning, pays 2x
    TOUCHDOWNS = "touchdowns"  # Bet on exact touchdowns, pays 5x
    INJURIES = "injuries"  # Bet on exact injuries/casualties, pays 7x


class BetStatus:
    """Bet status constants."""
    PENDING = "pending"  # Match not yet played
    WON = "won"  # Bet won
    LOST = "lost"  # Bet lost


# Payout multipliers for each bet type
BET_PAYOUTS = {
    BetType.WIN: 2,
    BetType.TOUCHDOWNS: 5,
    BetType.INJURIES: 7,
}

# Maximum bet amount
MAX_BET_AMOUNT = 50000


class Bet(db.Model):
    """A bet placed by a user on a match."""
    __tablename__ = "bets"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    
    # Bet details
    bet_type = db.Column(db.String(20), nullable=False)  # win, touchdowns, injuries
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)  # Team being bet on
    target_value = db.Column(db.Integer)  # For touchdowns/injuries bets, the exact number predicted
    amount = db.Column(db.Integer, nullable=False)  # Bet amount (max 50000)
    
    # Result
    status = db.Column(db.String(20), default=BetStatus.PENDING)  # pending, won, lost
    payout = db.Column(db.Integer, default=0)  # Amount won (0 if lost)
    
    # Timestamps
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship("User", backref=db.backref("bets", lazy="dynamic"))
    match = db.relationship("Match", backref=db.backref("bets", lazy="dynamic"))
    team = db.relationship("Team", backref=db.backref("bets_on", lazy="dynamic"))
    
    def __repr__(self) -> str:
        return f"<Bet {self.id}: {self.user.username} on {self.team.name}>"
    
    @property
    def multiplier(self) -> int:
        """Get the payout multiplier for this bet type."""
        return BET_PAYOUTS.get(self.bet_type, 1)
    
    @property
    def potential_payout(self) -> int:
        """Calculate potential payout if bet wins."""
        return self.amount * self.multiplier
    
    def resolve(self, match) -> bool:
        """
        Resolve the bet based on match results.
        Returns True if bet won, False if lost.
        """
        if self.status != BetStatus.PENDING:
            return self.status == BetStatus.WON
        
        won = False
        
        # Determine if this bet is on home or away team
        is_home = self.team_id == match.home_team_id
        
        if self.bet_type == BetType.WIN:
            # Check if the team won
            if is_home:
                won = match.home_score > match.away_score
            else:
                won = match.away_score > match.home_score
                
        elif self.bet_type == BetType.TOUCHDOWNS:
            # Check if team scored exact touchdowns
            if is_home:
                won = match.home_score == self.target_value
            else:
                won = match.away_score == self.target_value
                
        elif self.bet_type == BetType.INJURIES:
            # Check if team achieved exact injuries/casualties
            if is_home:
                won = match.home_casualties == self.target_value
            else:
                won = match.away_casualties == self.target_value
        
        # Update bet status
        self.resolved_at = datetime.utcnow()
        if won:
            self.status = BetStatus.WON
            self.payout = self.potential_payout
        else:
            self.status = BetStatus.LOST
            self.payout = 0
        
        return won
    
    def get_bet_description(self, lang: str = "en") -> str:
        """Get a human-readable description of the bet."""
        team_name = self.team.name
        
        if lang == "es":
            if self.bet_type == BetType.WIN:
                return f"{team_name} gana el partido"
            elif self.bet_type == BetType.TOUCHDOWNS:
                return f"{team_name} anota exactamente {self.target_value} touchdown(s)"
            elif self.bet_type == BetType.INJURIES:
                return f"{team_name} causa exactamente {self.target_value} baja(s)"
        else:
            if self.bet_type == BetType.WIN:
                return f"{team_name} wins the match"
            elif self.bet_type == BetType.TOUCHDOWNS:
                return f"{team_name} scores exactly {self.target_value} touchdown(s)"
            elif self.bet_type == BetType.INJURIES:
                return f"{team_name} inflicts exactly {self.target_value} casualty(ies)"
        
        return "Unknown bet"

class AIBet(Bet):
    """A bet that uses LLMs to estimate the multiplier."""
    
    # Store LLM response data
    ai_multiplier = db.Column(db.Float)
    ai_rationale = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)  # 0-1 confidence score
    
    __mapper_args__ = {
        'polymorphic_identity': 'ai_bet',
    }
    
    # Multiplier bounds
    MIN_MULTIPLIER = 1.01
    MAX_MULTIPLIER = 100.0
    DEFAULT_MULTIPLIER = 2.0
    
    def _gather_team_stats(self, team) -> dict:
        """Gather comprehensive statistics for a team."""
        return {
            "name": team.name,
            "race": team.race.name,
            "team_value": team.current_tv,
            "treasury": team.treasury,
            "rerolls": team.rerolls,
            "fan_factor": team.fan_factor,
            "has_apothecary": team.has_apothecary,
            "assistant_coaches": team.assistant_coaches,
            "cheerleaders": team.cheerleaders,
            "record": {
                "games_played": team.games_played,
                "wins": team.wins,
                "draws": team.draws,
                "losses": team.losses,
                "win_rate": round(team.wins / max(team.games_played, 1) * 100, 1),
            },
            "scoring": {
                "touchdowns_for": team.touchdowns_for,
                "touchdowns_against": team.touchdowns_against,
                "td_difference": team.touchdowns_for - team.touchdowns_against,
            },
            "casualties": {
                "inflicted": team.casualties_inflicted,
                "suffered": team.casualties_suffered,
                "difference": team.casualties_inflicted - team.casualties_suffered,
            },
        }
    
    def _gather_player_stats(self, team) -> list[dict]:
        """Gather statistics for all active players on a team."""
        players = []
        for player in team.players.filter_by(is_active=True, is_dead=False).all():
            player_data = {
                "name": player.name,
                "position": player.position.name,
                "number": player.number,
                "stats": {
                    "MA": player.movement,
                    "ST": player.strength,
                    "AG": player.agility,
                    "PA": player.passing,
                    "AV": player.armor,
                },
                "experience": {
                    "spp": player.spp,
                    "level": player.level,
                    "games_played": player.games_played,
                },
                "career": {
                    "touchdowns": player.touchdowns,
                    "casualties": player.casualties_inflicted,
                    "completions": player.completions,
                    "interceptions": player.interceptions,
                    "mvp_awards": player.mvp_awards,
                },
                "status": {
                    "miss_next_game": player.miss_next_game,
                    "niggling_injuries": player.niggling_injuries,
                },
                "skills": player.get_skill_list() if hasattr(player, 'get_skill_list') else [],
            }
            players.append(player_data)
        return players
    
    def _build_prompt(self, home_team_data: dict, away_team_data: dict, 
                      home_players: list, away_players: list) -> str:
        """Build the prompt for the LLM."""
        bet_description = self.get_bet_description()
        
        prompt = f"""You are an expert Blood Bowl analyst. Analyze the following match and betting scenario to estimate a fair multiplier.

## The Bet
{bet_description}
Bet Type: {self.bet_type}
Target Team: {self.team.name}
{"Target Value: " + str(self.target_value) if self.target_value is not None else ""}

## Home Team: {home_team_data['name']}
Race: {home_team_data['race']}
Team Value: {home_team_data['team_value']:,}g
Record: {home_team_data['record']['wins']}W-{home_team_data['record']['draws']}D-{home_team_data['record']['losses']}L ({home_team_data['record']['win_rate']}% win rate)
Touchdowns: {home_team_data['scoring']['touchdowns_for']} for / {home_team_data['scoring']['touchdowns_against']} against
Casualties: {home_team_data['casualties']['inflicted']} inflicted / {home_team_data['casualties']['suffered']} suffered
Rerolls: {home_team_data['rerolls']} | Fan Factor: {home_team_data['fan_factor']}

### Home Players ({len(home_players)} active):
"""
        for p in home_players[:11]:  # Limit to first 11 for prompt size
            skills_str = ", ".join(p['skills'][:5]) if p['skills'] else "None"
            prompt += f"- {p['name']} ({p['position']}): MA{p['stats']['MA']} ST{p['stats']['ST']} AG{p['stats']['AG']} AV{p['stats']['AV']} | {p['career']['touchdowns']}TD {p['career']['casualties']}CAS | Skills: {skills_str}\n"
        
        prompt += f"""
## Away Team: {away_team_data['name']}
Race: {away_team_data['race']}
Team Value: {away_team_data['team_value']:,}g
Record: {away_team_data['record']['wins']}W-{away_team_data['record']['draws']}D-{away_team_data['record']['losses']}L ({away_team_data['record']['win_rate']}% win rate)
Touchdowns: {away_team_data['scoring']['touchdowns_for']} for / {away_team_data['scoring']['touchdowns_against']} against
Casualties: {away_team_data['casualties']['inflicted']} inflicted / {away_team_data['casualties']['suffered']} suffered
Rerolls: {away_team_data['rerolls']} | Fan Factor: {away_team_data['fan_factor']}

### Away Players ({len(away_players)} active):
"""
        for p in away_players[:11]:
            skills_str = ", ".join(p['skills'][:5]) if p['skills'] else "None"
            prompt += f"- {p['name']} ({p['position']}): MA{p['stats']['MA']} ST{p['stats']['ST']} AG{p['stats']['AG']} AV{p['stats']['AV']} | {p['career']['touchdowns']}TD {p['career']['casualties']}CAS | Skills: {skills_str}\n"
        
        prompt += f"""
## Task
Based on the teams' and player's statistics, and the specific bet type, estimate a fair payout multiplier.

Consider:
1. Team strength comparison (TV, record, player quality)
2. Race matchup advantages/disadvantages
3. Historical performance for the team (TDs, casualties, throws, interceptions)
4. Historical performance for the players mentioned on the bet (TDs, casualties, throws, interceptions)
5. Bet difficulty (exact predictions are harder than win/lose)
6. Blood Bowl variance and unpredictability

Respond ONLY with valid JSON in this exact format:
{{
    "multiplier": <number between {self.MIN_MULTIPLIER} and {self.MAX_MULTIPLIER}>,
    "confidence": <number between 0 and 1>,
    "rationale": "<brief explanation of your analysis>"
}}"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> Optional[dict]:
        """Call the Google Gemini API to get multiplier estimation."""
        try:
            from google import genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return None
            
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            
            # Parse the response
            response_text = response.text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            return json.loads(response_text.strip())
            
        except ImportError:
            return None
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    
    def calculate_multiplier(self) -> float:
        """
        Calculate the multiplier using LLM analysis.
        
        The multiplier for an AIBet is calculated via the following process:
            1. Fetch both teams statistics
            2. Fetch the statistics for each player for each team
            3. Pass all the statistics to an LLM to estimate a multiplier within a certain range,
               as well as a rationale for the estimation
        
        Returns:
            The calculated multiplier (or default if LLM unavailable)
        """
        # Return cached value if already calculated
        if self.ai_multiplier is not None:
            return self.ai_multiplier
        
        try:
            match = self.match
            home_team = match.home_team
            away_team = match.away_team
            
            # Gather team statistics
            home_team_data = self._gather_team_stats(home_team)
            away_team_data = self._gather_team_stats(away_team)
            
            # Gather player statistics
            home_players = self._gather_player_stats(home_team)
            away_players = self._gather_player_stats(away_team)
            
            # Build prompt and call LLM
            prompt = self._build_prompt(home_team_data, away_team_data, 
                                        home_players, away_players)
            result = self._call_llm(prompt)
            
            if result:
                # Validate and clamp multiplier
                multiplier = float(result.get("multiplier", self.DEFAULT_MULTIPLIER))
                multiplier = max(self.MIN_MULTIPLIER, min(self.MAX_MULTIPLIER, multiplier))
                
                # Store results
                self.ai_multiplier = multiplier
                self.ai_rationale = result.get("rationale", "")
                self.ai_confidence = float(result.get("confidence", 0.5))
                
                return multiplier
            
        except Exception:
            pass
        
        # Fallback to default multiplier
        self.ai_multiplier = self.DEFAULT_MULTIPLIER
        self.ai_rationale = "Default multiplier (LLM unavailable)"
        self.ai_confidence = 0.0
        return self.DEFAULT_MULTIPLIER
    
    @property
    def multiplier(self) -> float:
        """Get the payout multiplier for this AI bet."""
        return self.calculate_multiplier()
    
    @property
    def potential_payout(self) -> int:
        """Calculate potential payout if bet wins."""
        return int(self.amount * self.multiplier)

class BetNotification(db.Model):
    """Notification for bet results."""
    __tablename__ = "bet_notifications"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    bet_id = db.Column(db.Integer, db.ForeignKey("bets.id"), nullable=False)
    
    # Notification status
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship("User", backref=db.backref("bet_notifications", lazy="dynamic"))
    bet = db.relationship("Bet", backref=db.backref("notification", uselist=False))
    
    def __repr__(self) -> str:
        return f"<BetNotification {self.id} for user {self.user_id}>"
    
    def mark_as_read(self) -> None:
        """Mark this notification as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def get_message(self, lang: str = "en") -> str:
        """Get the notification message."""
        bet = self.bet
        match = bet.match
        
        home_team = match.home_team.name
        away_team = match.away_team.name
        match_result = f"{home_team} {match.home_score} - {match.away_score} {away_team}"
        
        if lang == "es":
            if bet.status == BetStatus.WON:
                return (
                    f"🎉 ¡Ganaste tu apuesta! {bet.get_bet_description('es')} "
                    f"({match_result}). "
                    f"Apostaste {bet.amount:,}g y ganaste {bet.payout:,}g."
                )
            else:
                return (
                    f"😞 Perdiste tu apuesta. {bet.get_bet_description('es')} "
                    f"({match_result}). "
                    f"Perdiste {bet.amount:,}g."
                )
        else:
            if bet.status == BetStatus.WON:
                return (
                    f"🎉 You won your bet! {bet.get_bet_description('en')} "
                    f"({match_result}). "
                    f"You bet {bet.amount:,}g and won {bet.payout:,}g."
                )
            else:
                return (
                    f"😞 You lost your bet. {bet.get_bet_description('en')} "
                    f"({match_result}). "
                    f"You lost {bet.amount:,}g."
                )

