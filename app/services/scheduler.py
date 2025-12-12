"""Schedule generation service."""
from typing import List, Tuple
from app.models import Team


def generate_round_robin_schedule(teams: List[Team]) -> List[List[Tuple[Team, Team]]]:
    """
    Generate a round-robin schedule for the given teams.
    
    Returns a list of rounds, where each round is a list of (home, away) tuples.
    Uses the circle method for scheduling.
    """
    n = len(teams)
    
    # If odd number of teams, add a "bye" placeholder
    if n % 2 == 1:
        teams = teams + [None]  # type: ignore
        n += 1
    
    schedule = []
    team_list = list(teams)
    
    # Number of rounds needed
    num_rounds = n - 1
    
    for round_num in range(num_rounds):
        round_matches = []
        
        for i in range(n // 2):
            home = team_list[i]
            away = team_list[n - 1 - i]
            
            # Skip bye matches
            if home is not None and away is not None:
                # Alternate home/away to balance
                if round_num % 2 == 0:
                    round_matches.append((home, away))
                else:
                    round_matches.append((away, home))
        
        schedule.append(round_matches)
        
        # Rotate teams (keep first team fixed)
        team_list = [team_list[0]] + [team_list[-1]] + team_list[1:-1]
    
    return schedule


def generate_swiss_pairings(standings: list, round_number: int) -> List[Tuple]:
    """
    Generate Swiss-system pairings based on current standings.
    
    Teams are paired with opponents who have similar scores,
    avoiding rematches where possible.
    """
    # Sort by points, then by tiebreakers
    sorted_standings = sorted(
        standings,
        key=lambda s: (s.points, s.touchdown_diff, s.touchdowns_for),
        reverse=True
    )
    
    teams = [s.team for s in sorted_standings]
    paired = set()
    matches = []
    
    for team in teams:
        if team.id in paired:
            continue
        
        # Find best opponent (closest in standings, not yet played)
        for opponent_standing in sorted_standings:
            opponent = opponent_standing.team
            if opponent.id == team.id:
                continue
            if opponent.id in paired:
                continue
            # TODO: Check if teams have already played each other
            
            matches.append((team, opponent))
            paired.add(team.id)
            paired.add(opponent.id)
            break
    
    return matches


def generate_knockout_bracket(teams: List[Team], seeded: bool = True) -> dict:
    """
    Generate a single-elimination bracket.
    
    Returns bracket structure with rounds and matchups.
    """
    n = len(teams)
    
    # Find next power of 2
    bracket_size = 1
    while bracket_size < n:
        bracket_size *= 2
    
    # Number of byes needed
    num_byes = bracket_size - n
    
    if seeded:
        # Seed teams (assuming teams are ordered by seed)
        seeded_teams = list(teams)
    else:
        # Random order
        import random
        seeded_teams = list(teams)
        random.shuffle(seeded_teams)
    
    # Add byes to lower seeds
    for _ in range(num_byes):
        seeded_teams.append(None)
    
    # Create bracket structure
    bracket = {
        "size": bracket_size,
        "rounds": [],
        "teams": seeded_teams
    }
    
    # Generate first round matchups
    first_round = []
    for i in range(bracket_size // 2):
        high_seed = seeded_teams[i]
        low_seed = seeded_teams[bracket_size - 1 - i]
        first_round.append({
            "match_number": i + 1,
            "team1": high_seed,
            "team2": low_seed,
            "winner": high_seed if low_seed is None else None  # Auto-advance for byes
        })
    
    bracket["rounds"].append(first_round)
    
    return bracket

