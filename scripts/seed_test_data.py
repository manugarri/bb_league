#!/usr/bin/env python
"""Script to populate the database with test data for development."""
import argparse
import random
import sys
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Team, Player, Race, Position, League, LeagueTeam, Match, MatchPlayerStats, Standing, Season


def create_test_users(n_players: int = 4, n_admin_players: int = 1) -> list[User]:
    """Create test users (admin and regular users).
    
    Args:
        n_players: Total number of users to create
        n_admin_players: Number of users that should be admins (first N users)
    
    Returns:
        List of User objects
    """
    users = []
    
    for i in range(1, n_players + 1):
        is_admin = i <= n_admin_players
        
        if is_admin:
            username = "admin" if i == 1 else f"admin{i}"
            display_name = "Administrator" if i == 1 else f"Administrator {i}"
            role = "admin"
        else:
            # For non-admins, number them sequentially starting from 1
            user_num = i - n_admin_players
            username = f"user{user_num}"
            display_name = f"Coach {user_num}"
            role = "coach"
        
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@bloodbowl.local",
                role=role,
                display_name=display_name
            )
            user.set_password(username)  # password = username
            db.session.add(user)
            role_label = "Admin" if is_admin else "Coach"
            print(f"  [+] Created {role_label} '{username}' ({username}:{username})")
        else:
            print(f"  [=] User '{username}' already exists")
        users.append(user)
    
    db.session.commit()
    return users


def create_team_for_user(user: User, team_name: str, race: Race, n_roster_players: int = 4) -> Team:
    """Create a team with players for a user.
    
    Args:
        user: The user who will own the team
        team_name: Name of the team
        race: Race object for the team
        n_roster_players: Number of players to add to roster
    
    Returns:
        Created Team object or None if failed
    """
    # Check if team with this exact name already exists for this user
    existing_team = Team.query.filter_by(name=team_name, coach_id=user.id).first()
    if existing_team:
        print(f"  [=] Team '{existing_team.name}' already exists for {user.username}")
        return existing_team
    
    # Create the team
    team = Team(
        name=team_name,
        coach_id=user.id,
        race_id=race.id,
        treasury=900000,
        rerolls=2,
        fan_factor=1
    )
    db.session.add(team)
    db.session.flush()  # Get team ID
    
    # Get positions for this race (prioritize Linemen type positions)
    positions = Position.query.filter_by(race_id=race.id).all()
    if not positions:
        print(f"  [!] No positions found for race '{race.name}'!")
        return team
    
    # Find lineman position (most common) and other positions
    lineman_pos = None
    other_positions = []
    for pos in positions:
        pos_name_lower = pos.name.lower()
        if any(term in pos_name_lower for term in ['lineman', 'linewoman', 'linerat', 'skeleton', 'zombie', 'rotter', 'beastman']):
            lineman_pos = pos
        else:
            other_positions.append(pos)
    
    # If no lineman found, use first position
    if not lineman_pos:
        lineman_pos = positions[0]
    
    # Generate player names
    base_names = ["Griff", "Bruiser", "Speedy", "Blocker", "Crusher", "Swift", 
                  "Tank", "Flash", "Hammer", "Storm", "Blade", "Thunder",
                  "Shadow", "Spike", "Fang", "Ripper", "Slasher", "Basher"]
    
    for idx in range(n_roster_players):
        # Mix linemen and special players (75% linemen, 25% special)
        if idx < (n_roster_players * 3 // 4) or not other_positions:
            pos = lineman_pos
        else:
            pos = other_positions[idx % len(other_positions)]
        
        name = base_names[idx % len(base_names)]
        player = Player(
            team_id=team.id,
            position_id=pos.id,
            name=f"{name} {team_name[:3]}",
            number=idx + 1,
            movement=pos.movement,
            strength=pos.strength,
            agility=pos.agility,
            passing=pos.passing,
            armor=pos.armor,
            spp=0,
            level=1,
            value=pos.cost
        )
        db.session.add(player)
    
    # Update team TV
    team.calculate_tv()
    db.session.commit()
    
    print(f"  [+] Created team '{team_name}' ({race.name}) with {n_roster_players} players for {user.username}")
    return team


def create_teams_for_users(users: list[User], n_teams_per_player: int = 1, n_roster_players: int = 4) -> list[Team]:
    """Create teams for all users.
    
    Args:
        users: List of users to create teams for
        n_teams_per_player: Number of teams each user should have
        n_roster_players: Number of players per team
    
    Returns:
        List of all created teams
    """
    all_teams = []
    
    # Get available races
    available_races = Race.query.all()
    if not available_races:
        print("  [!] No races available. Run 'make seed' first.")
        return all_teams
    
    # Team name prefixes/suffixes for variety
    prefixes = ["Mighty", "Brutal", "Swift", "Dark", "Iron", "Blood", "Storm", "Shadow", "Doom", "Fire"]
    suffixes = ["Crushers", "Raiders", "Warriors", "Hunters", "Slayers", "Titans", "Legends", "Demons", "Knights", "Giants"]
    
    team_counter = 0
    for user in users:
        for team_num in range(n_teams_per_player):
            # Cycle through races
            race = available_races[team_counter % len(available_races)]
            
            # Generate unique team name
            prefix = prefixes[team_counter % len(prefixes)]
            suffix = suffixes[(team_counter // len(prefixes)) % len(suffixes)]
            team_name = f"{prefix} {suffix}"
            
            team = create_team_for_user(user, team_name, race, n_roster_players)
            if team:
                all_teams.append(team)
            
            team_counter += 1
    
    return all_teams


def create_test_leagues(commissioner: User, teams: list[Team], n_leagues: int = 1, 
                        max_teams_per_league: int = 16) -> list[League]:
    """Create test leagues and add random teams up to max_teams limit.
    
    Args:
        commissioner: User who will be commissioner of all leagues
        teams: List of teams to randomly select from
        n_leagues: Number of leagues to create
        max_teams_per_league: Maximum teams per league (fixed at 16 by default)
    
    Returns:
        List of created leagues
    """
    leagues = []
    
    for league_num in range(1, n_leagues + 1):
        league_name = "test-league" if league_num == 1 else f"test-league-{league_num}"
        
        # Check if league exists
        existing = League.query.filter_by(name=league_name).first()
        if existing:
            print(f"  [=] League '{league_name}' already exists")
            leagues.append(existing)
            continue
        
        # Create the league with fixed max_teams
        league = League(
            name=league_name,
            commissioner_id=commissioner.id,
            description=f"Test league #{league_num} for development and testing purposes.",
            format="round_robin",
            max_teams=max_teams_per_league,
            min_teams=2,
            min_roster_size=4,
            max_roster_size=16,
            allow_star_players=True,
            status="registration",
            registration_open=True,
            is_public=True
        )
        db.session.add(league)
        db.session.flush()
        
        # Create initial season for the league
        season = Season(
            league_id=league.id,
            name="Season 1",
            number=1,
            is_active=True
        )
        db.session.add(season)
        db.session.flush()
        
        print(f"  [+] Created league '{league_name}' (max {max_teams_per_league} teams)")
        
        # Filter out None teams
        valid_teams = [t for t in teams if t is not None]
        
        # Randomly shuffle and select up to max_teams_per_league teams
        shuffled_teams = list(valid_teams)
        random.shuffle(shuffled_teams)
        teams_to_add = shuffled_teams[:max_teams_per_league]
        
        # Add selected teams to this league
        teams_added = 0
        for team in teams_to_add:
            # Check if team is already in THIS league
            existing_entry = LeagueTeam.query.filter_by(
                league_id=league.id, 
                team_id=team.id
            ).first()
            
            if existing_entry:
                continue
            
            league_team = LeagueTeam(
                league_id=league.id,
                team_id=team.id,
                is_approved=True,
                approved_at=datetime.utcnow()
            )
            db.session.add(league_team)
            teams_added += 1
        
        print(f"      Added {teams_added}/{len(valid_teams)} teams to {league_name}")
        leagues.append(league)
    
    db.session.commit()
    return leagues


def simulate_match_results(match: Match) -> None:
    """Simulate detailed match results with player statistics.
    
    Args:
        match: The match to simulate results for
    """
    # Random scores (weighted towards lower scores, typical for Blood Bowl)
    home_score = random.choices([0, 1, 2, 3, 4], weights=[15, 35, 30, 15, 5])[0]
    away_score = random.choices([0, 1, 2, 3, 4], weights=[15, 35, 30, 15, 5])[0]
    
    # Random casualties (weighted towards lower numbers)
    home_casualties = random.choices([0, 1, 2, 3, 4, 5], weights=[20, 30, 25, 15, 7, 3])[0]
    away_casualties = random.choices([0, 1, 2, 3, 4, 5], weights=[20, 30, 25, 15, 7, 3])[0]
    
    # Set match results
    match.home_score = home_score
    match.away_score = away_score
    match.home_casualties = home_casualties
    match.away_casualties = away_casualties
    match.home_winnings = random.randint(20000, 70000)
    match.away_winnings = random.randint(20000, 70000)
    match.home_fan_factor_change = random.choice([-1, 0, 0, 0, 1])
    match.away_fan_factor_change = random.choice([-1, 0, 0, 0, 1])
    match.status = "completed"
    match.played_date = datetime.utcnow() - timedelta(days=random.randint(1, 7))
    
    # Get active players for both teams
    home_players = list(match.home_team.players.filter_by(is_active=True, is_dead=False).all())
    away_players = list(match.away_team.players.filter_by(is_active=True, is_dead=False).all())
    
    # Injury types for random injuries
    injury_types = [None, None, None, None, None, "Badly Hurt", "Badly Hurt", "Miss Next Game", "Niggling Injury"]
    
    # Create player stats for home team
    home_td_remaining = home_score
    home_cas_remaining = home_casualties
    
    for player in home_players:
        # Distribute touchdowns
        player_tds = 0
        if home_td_remaining > 0 and random.random() < 0.4:
            player_tds = min(random.randint(1, 2), home_td_remaining)
            home_td_remaining -= player_tds
        
        # Distribute casualties
        player_cas = 0
        if home_cas_remaining > 0 and random.random() < 0.3:
            player_cas = min(random.randint(1, 2), home_cas_remaining)
            home_cas_remaining -= player_cas
        
        # Random completions, interceptions
        player_completions = random.choices([0, 0, 0, 1, 2, 3], weights=[50, 20, 10, 10, 7, 3])[0]
        player_interceptions = random.choices([0, 0, 0, 0, 1], weights=[70, 15, 10, 4, 1])[0]
        player_deflections = random.choices([0, 0, 0, 1], weights=[70, 15, 10, 5])[0]
        
        # Random injury suffered (from away team casualties)
        injury_result = None
        if away_casualties > 0 and random.random() < (away_casualties * 0.1):
            injury_result = random.choice(injury_types)
        
        stats = MatchPlayerStats(
            match_id=match.id,
            player_id=player.id,
            team_id=match.home_team_id,
            touchdowns=player_tds,
            completions=player_completions,
            interceptions=player_interceptions,
            deflections=player_deflections,
            casualties_inflicted=player_cas,
            injury_result=injury_result,
            is_mvp=False
        )
        stats.calculate_spp()
        db.session.add(stats)
        
        # Update player career stats
        player.touchdowns = (player.touchdowns or 0) + player_tds
        player.casualties_inflicted = (player.casualties_inflicted or 0) + player_cas
        player.completions = (player.completions or 0) + player_completions
        player.interceptions = (player.interceptions or 0) + player_interceptions
        player.deflections = (player.deflections or 0) + player_deflections
        player.games_played = (player.games_played or 0) + 1
        player.spp = (player.spp or 0) + stats.spp_earned
        
        # Apply injury effects
        if injury_result == "Miss Next Game":
            player.miss_next_game = True
        elif injury_result == "Niggling Injury":
            player.niggling_injuries = (player.niggling_injuries or 0) + 1
    
    # Select MVP for home team
    if home_players:
        mvp_player = random.choice(home_players)
        mvp_stats = MatchPlayerStats.query.filter_by(
            match_id=match.id, player_id=mvp_player.id
        ).first()
        if mvp_stats:
            mvp_stats.is_mvp = True
            mvp_stats.calculate_spp()
            mvp_player.mvp_awards = (mvp_player.mvp_awards or 0) + 1
            mvp_player.spp = (mvp_player.spp or 0) + 4  # MVP bonus
    
    # Create player stats for away team
    away_td_remaining = away_score
    away_cas_remaining = away_casualties
    
    for player in away_players:
        # Distribute touchdowns
        player_tds = 0
        if away_td_remaining > 0 and random.random() < 0.4:
            player_tds = min(random.randint(1, 2), away_td_remaining)
            away_td_remaining -= player_tds
        
        # Distribute casualties
        player_cas = 0
        if away_cas_remaining > 0 and random.random() < 0.3:
            player_cas = min(random.randint(1, 2), away_cas_remaining)
            away_cas_remaining -= player_cas
        
        # Random completions, interceptions
        player_completions = random.choices([0, 0, 0, 1, 2, 3], weights=[50, 20, 10, 10, 7, 3])[0]
        player_interceptions = random.choices([0, 0, 0, 0, 1], weights=[70, 15, 10, 4, 1])[0]
        player_deflections = random.choices([0, 0, 0, 1], weights=[70, 15, 10, 5])[0]
        
        # Random injury suffered (from home team casualties)
        injury_result = None
        if home_casualties > 0 and random.random() < (home_casualties * 0.1):
            injury_result = random.choice(injury_types)
        
        stats = MatchPlayerStats(
            match_id=match.id,
            player_id=player.id,
            team_id=match.away_team_id,
            touchdowns=player_tds,
            completions=player_completions,
            interceptions=player_interceptions,
            deflections=player_deflections,
            casualties_inflicted=player_cas,
            injury_result=injury_result,
            is_mvp=False
        )
        stats.calculate_spp()
        db.session.add(stats)
        
        # Update player career stats
        player.touchdowns = (player.touchdowns or 0) + player_tds
        player.casualties_inflicted = (player.casualties_inflicted or 0) + player_cas
        player.completions = (player.completions or 0) + player_completions
        player.interceptions = (player.interceptions or 0) + player_interceptions
        player.deflections = (player.deflections or 0) + player_deflections
        player.games_played = (player.games_played or 0) + 1
        player.spp = (player.spp or 0) + stats.spp_earned
        
        # Apply injury effects
        if injury_result == "Miss Next Game":
            player.miss_next_game = True
        elif injury_result == "Niggling Injury":
            player.niggling_injuries = (player.niggling_injuries or 0) + 1
    
    # Select MVP for away team
    if away_players:
        mvp_player = random.choice(away_players)
        mvp_stats = MatchPlayerStats.query.filter_by(
            match_id=match.id, player_id=mvp_player.id
        ).first()
        if mvp_stats:
            mvp_stats.is_mvp = True
            mvp_stats.calculate_spp()
            mvp_player.mvp_awards = (mvp_player.mvp_awards or 0) + 1
            mvp_player.spp = (mvp_player.spp or 0) + 4  # MVP bonus
    
    # Update team statistics
    match.home_team.games_played = (match.home_team.games_played or 0) + 1
    match.away_team.games_played = (match.away_team.games_played or 0) + 1
    match.home_team.touchdowns_for = (match.home_team.touchdowns_for or 0) + home_score
    match.home_team.touchdowns_against = (match.home_team.touchdowns_against or 0) + away_score
    match.away_team.touchdowns_for = (match.away_team.touchdowns_for or 0) + away_score
    match.away_team.touchdowns_against = (match.away_team.touchdowns_against or 0) + home_score
    match.home_team.casualties_inflicted = (match.home_team.casualties_inflicted or 0) + home_casualties
    match.home_team.casualties_suffered = (match.home_team.casualties_suffered or 0) + away_casualties
    match.away_team.casualties_inflicted = (match.away_team.casualties_inflicted or 0) + away_casualties
    match.away_team.casualties_suffered = (match.away_team.casualties_suffered or 0) + home_casualties
    
    # Update wins/draws/losses
    if home_score > away_score:
        match.home_team.wins = (match.home_team.wins or 0) + 1
        match.away_team.losses = (match.away_team.losses or 0) + 1
    elif away_score > home_score:
        match.away_team.wins = (match.away_team.wins or 0) + 1
        match.home_team.losses = (match.home_team.losses or 0) + 1
    else:
        match.home_team.draws = (match.home_team.draws or 0) + 1
        match.away_team.draws = (match.away_team.draws or 0) + 1
    
    # Update league standings
    update_standings(match)


def update_standings(match: Match) -> None:
    """Update league standings from match result.
    
    League points are awarded as follows:
    - Victory: +3 league points
    - Tie: +1 league point
    - 3+ touchdowns scored: +1 league point
    - Opponent scores 3+ touchdowns: +1 league point
    - 3+ casualties caused: +1 league point
    """
    if not match.league:
        return
    
    season = match.league.current_season
    if not season:
        return
    
    # Get or create standings for home team
    home_standing = Standing.query.filter_by(
        season_id=season.id,
        team_id=match.home_team_id
    ).first()
    
    if not home_standing:
        home_standing = Standing(
            season_id=season.id,
            team_id=match.home_team_id
        )
        db.session.add(home_standing)
    
    # Get or create standings for away team
    away_standing = Standing.query.filter_by(
        season_id=season.id,
        team_id=match.away_team_id
    ).first()
    
    if not away_standing:
        away_standing = Standing(
            season_id=season.id,
            team_id=match.away_team_id
        )
        db.session.add(away_standing)
    
    # Update standings using the model's method
    home_standing.update_from_match(True, match)
    away_standing.update_from_match(False, match)


def generate_round_robin_rounds(teams: list, n_rounds: int = 3) -> list[list[tuple]]:
    """Generate round-robin pairings for multiple rounds.
    
    Uses a rotation algorithm to ensure each team plays different opponents each round.
    
    Args:
        teams: List of teams to pair
        n_rounds: Number of rounds to generate
    
    Returns:
        List of rounds, where each round is a list of (home_team, away_team) tuples
    """
    if len(teams) < 2:
        return []
    
    # Make a copy and add a dummy if odd number of teams
    team_list = list(teams)
    if len(team_list) % 2 == 1:
        team_list.append(None)  # Bye
    
    n_teams = len(team_list)
    rounds = []
    
    # Generate rounds using circle method
    for round_num in range(n_rounds):
        round_matches = []
        
        # Rotate the list (except first element) for each round
        if round_num > 0:
            # Rotate: keep first element, rotate rest
            team_list = [team_list[0]] + [team_list[-1]] + team_list[1:-1]
        
        # Pair teams: first with last, second with second-to-last, etc.
        for i in range(n_teams // 2):
            home = team_list[i]
            away = team_list[n_teams - 1 - i]
            
            # Skip bye matches
            if home is None or away is None:
                continue
            
            # Alternate home/away based on round number
            if round_num % 2 == 1:
                home, away = away, home
            
            round_matches.append((home, away))
        
        rounds.append(round_matches)
    
    return rounds


def create_league_matches(leagues: list[League], n_leagues_in_progress: int, 
                          n_rounds: int = 3, n_completed_rounds: int = 2) -> tuple[int, int]:
    """Create matches for leagues in progress.
    
    Args:
        leagues: List of all leagues
        n_leagues_in_progress: Number of leagues to create matches for
        n_rounds: Total number of rounds to create
        n_completed_rounds: Number of rounds to simulate results for
    
    Returns:
        Tuple of (matches_created, matches_completed)
    """
    if n_leagues_in_progress <= 0:
        return 0, 0
    
    total_created = 0
    total_completed = 0
    
    for i, league in enumerate(leagues[:n_leagues_in_progress]):
        # Get teams in this league
        league_teams = [lt.team for lt in league.teams.filter_by(is_approved=True).all()]
        
        if len(league_teams) < 2:
            print(f"  [!] League '{league.name}' has fewer than 2 teams, skipping")
            continue
        
        # Update league status to active
        league.status = "active"
        league.registration_open = False
        
        print(f"\n  [+] Creating {n_rounds} rounds for league '{league.name}' ({len(league_teams)} teams)")
        print(f"      Completing {n_completed_rounds} rounds, leaving {n_rounds - n_completed_rounds} scheduled")
        
        # Generate round-robin pairings
        rounds = generate_round_robin_rounds(league_teams, n_rounds)
        
        for round_num, round_matches in enumerate(rounds, start=1):
            is_completed_round = round_num <= n_completed_rounds
            round_status = "COMPLETED" if is_completed_round else "SCHEDULED"
            
            print(f"\n      Round {round_num} [{round_status}]:")
            
            for home_team, away_team in round_matches:
                # Check if match already exists
                existing_match = Match.query.filter(
                    Match.league_id == league.id,
                    Match.round_number == round_num,
                    ((Match.home_team_id == home_team.id) & (Match.away_team_id == away_team.id)) |
                    ((Match.home_team_id == away_team.id) & (Match.away_team_id == home_team.id))
                ).first()
                
                if existing_match:
                    print(f"        [=] {home_team.name} vs {away_team.name} already exists")
                    continue
                
                # Set scheduled date based on round
                if is_completed_round:
                    # Past date for completed rounds
                    scheduled_date = datetime.utcnow() - timedelta(days=(n_rounds - round_num + 1) * 7 + random.randint(0, 3))
                else:
                    # Future date for scheduled rounds
                    scheduled_date = datetime.utcnow() + timedelta(days=(round_num - n_completed_rounds) * 7 + random.randint(0, 3))
                
                # Create the match (include season_id for standings)
                match = Match(
                    league_id=league.id,
                    season_id=league.current_season.id if league.current_season else None,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    round_number=round_num,
                    scheduled_date=scheduled_date,
                    status="scheduled"
                )
                db.session.add(match)
                db.session.flush()  # Get match ID
                
                total_created += 1
                
                if is_completed_round:
                    # Simulate the match results
                    simulate_match_results(match)
                    total_completed += 1
                    
                    print(f"        [+] {home_team.name} {match.home_score}-{match.away_score} {away_team.name} "
                          f"(CAS: {match.home_casualties}-{match.away_casualties})")
                else:
                    print(f"        [~] {home_team.name} vs {away_team.name} (scheduled)")
        
        db.session.commit()
    
    return total_created, total_completed


def seed_test_data(n_players: int = 4, n_admin_players: int = 1, 
                   n_teams_per_player: int = 1, n_leagues: int = 1,
                   n_roster_players: int = 4, n_leagues_in_progress: int = 0):
    """Main function to seed all test data.
    
    Args:
        n_players: Total number of users to create
        n_admin_players: Number of admin users
        n_teams_per_player: Teams per user
        n_leagues: Number of leagues to create
        n_roster_players: Players per team roster
        n_leagues_in_progress: Number of leagues to simulate 1 round of matches
    """
    print("\n" + "=" * 60)
    print("Seeding Test Data")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  - Total users: {n_players}")
    print(f"  - Admin users: {n_admin_players}")
    print(f"  - Teams per user: {n_teams_per_player}")
    print(f"  - Leagues: {n_leagues}")
    print(f"  - Players per roster: {n_roster_players}")
    print(f"  - Leagues in progress: {n_leagues_in_progress}")
    
    # Create users
    print("\n[Users]")
    users = create_test_users(n_players, n_admin_players)
    
    if not users:
        print("[!] No users created. Aborting.")
        return
    
    # Create teams for each user
    print("\n[Teams]")
    teams = create_teams_for_users(users, n_teams_per_player, n_roster_players)
    
    # Get the first admin user as commissioner (or first user if no admins)
    commissioner = users[0]
    
    # Create leagues and add teams
    print("\n[Leagues]")
    leagues = create_test_leagues(commissioner, teams, n_leagues)
    
    # Simulate matches for leagues in progress
    matches_created = 0
    matches_completed = 0
    if n_leagues_in_progress > 0:
        print("\n[Match Simulation - 3 Rounds (2 Completed, 1 Scheduled)]")
        matches_created, matches_completed = create_league_matches(
            leagues, n_leagues_in_progress, 
            n_rounds=3, n_completed_rounds=2
        )
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Data Seeding Complete!")
    print("=" * 60)
    
    print("\nCredentials:")
    for user in users:
        role = "Administrator" if user.role == "admin" else "Coach"
        print(f"  - {user.username}:{user.username} ({role})")
    
    print(f"\nTeams ({len(teams)} total):")
    for team in teams[:10]:  # Show first 10
        if team:
            print(f"  - {team.name} ({team.race.name}) - {team.players.count()} players")
    if len(teams) > 10:
        print(f"  ... and {len(teams) - 10} more teams")
    
    print(f"\nLeagues ({len(leagues)} total):")
    for league in leagues:
        if league:
            status_label = f" [IN PROGRESS]" if league.status == "in_progress" else ""
            print(f"  - {league.name}: {league.team_count} teams enrolled{status_label}")
    
    if matches_created > 0:
        print(f"\nMatches created: {matches_created}")
        print(f"  - Completed: {matches_completed}")
        print(f"  - Scheduled: {matches_created - matches_completed}")
    print()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed the database with test data for development.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-p", "--n-players",
        type=int,
        default=4,
        help="Total number of users to create"
    )
    
    parser.add_argument(
        "-a", "--n-admin-players",
        type=int,
        default=1,
        help="Number of users that should be admins (first N users)"
    )
    
    parser.add_argument(
        "-t", "--n-teams-per-player",
        type=int,
        default=1,
        help="Number of teams to create per user"
    )
    
    parser.add_argument(
        "-l", "--n-leagues",
        type=int,
        default=1,
        help="Number of leagues to create"
    )
    
    parser.add_argument(
        "-r", "--n-roster-players",
        type=int,
        default=4,
        help="Number of players per team roster"
    )
    
    parser.add_argument(
        "-i", "--n-leagues-in-progress",
        type=int,
        default=0,
        help="Number of leagues to simulate 1 round of matches for (sets them to 'in_progress')"
    )
    
    return parser.parse_args()


def main():
    """Entry point for the script."""
    args = parse_args()
    
    # Validate arguments
    if args.n_admin_players > args.n_players:
        print(f"Error: n_admin_players ({args.n_admin_players}) cannot exceed n_players ({args.n_players})")
        sys.exit(1)
    
    if args.n_players < 1:
        print("Error: n_players must be at least 1")
        sys.exit(1)
    
    app = create_app()
    
    with app.app_context():
        try:
            seed_test_data(
                n_players=args.n_players,
                n_admin_players=args.n_admin_players,
                n_teams_per_player=args.n_teams_per_player,
                n_leagues=args.n_leagues,
                n_roster_players=args.n_roster_players,
                n_leagues_in_progress=args.n_leagues_in_progress
            )
        except Exception as e:
            print(f"\n[ERROR] {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
