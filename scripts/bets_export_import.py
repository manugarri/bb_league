#!/usr/bin/env python
"""Bet export and import utilities."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import User, Match, Team
from app.models.bet import Bet, BetNotification


def serialize_datetime(value):
    """Serialize datetime for JSON."""
    if value is None:
        return None
    return value.isoformat()


def deserialize_datetime(value):
    """Deserialize datetime from JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


def export_bets(output_file: str):
    """Export all bets to a JSON file."""
    app = create_app()
    
    with app.app_context():
        bets = Bet.query.all()
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "bets": [],
            "notifications": []
        }
        
        print(f"Exporting {len(bets)} bets...")
        
        for bet in bets:
            # Get related entity names for import lookup
            user = db.session.get(User, bet.user_id)
            match = db.session.get(Match, bet.match_id)
            team = db.session.get(Team, bet.team_id)
            
            bet_data = {
                "user_username": user.username if user else None,
                "match_id": bet.match_id,
                "home_team_name": match.home_team.name if match and match.home_team else None,
                "away_team_name": match.away_team.name if match and match.away_team else None,
                "league_name": match.league.name if match and match.league else None,
                "team_name": team.name if team else None,
                "bet_type": bet.bet_type,
                "target_value": bet.target_value,
                "amount": bet.amount,
                "status": bet.status,
                "payout": bet.payout,
                "placed_at": serialize_datetime(bet.placed_at),
                "resolved_at": serialize_datetime(bet.resolved_at),
                # AI bet specific fields
                "is_ai_bet": bet.type == "ai_bet" if hasattr(bet, 'type') else False,
                "ai_multiplier": getattr(bet, 'ai_multiplier', None),
                "ai_rationale": getattr(bet, 'ai_rationale', None),
                "ai_confidence": getattr(bet, 'ai_confidence', None),
            }
            export_data["bets"].append(bet_data)
        
        # Export notifications
        notifications = BetNotification.query.all()
        print(f"Exporting {len(notifications)} notifications...")
        
        for notification in notifications:
            user = db.session.get(User, notification.user_id)
            
            notification_data = {
                "user_username": user.username if user else None,
                "bet_index": None,  # Will be determined based on bet order
                "is_read": notification.is_read,
                "created_at": serialize_datetime(notification.created_at),
                "read_at": serialize_datetime(notification.read_at),
            }
            
            # Find the index of the related bet in our export
            for idx, bet in enumerate(bets):
                if bet.id == notification.bet_id:
                    notification_data["bet_index"] = idx
                    break
            
            export_data["notifications"].append(notification_data)
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nBets exported to: {output_path}")
        print(f"Total bets: {len(export_data['bets'])}")
        print(f"Total notifications: {len(export_data['notifications'])}")


def import_bets(input_file: str, reset: bool = False):
    """Import bets from a JSON file."""
    app = create_app()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    print(f"Importing from: {input_path}")
    print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
    print(f"Mode: {'RESET (clearing existing bets)' if reset else 'ADD (adding to existing)'}")
    
    with app.app_context():
        if reset:
            print("\nClearing existing bets...")
            BetNotification.query.delete()
            Bet.query.delete()
            db.session.commit()
            print("Existing bets cleared.")
        
        imported_bets = []
        bets_imported = 0
        bets_skipped = 0
        
        for bet_data in import_data.get("bets", []):
            # Find user by username
            user = User.query.filter_by(username=bet_data["user_username"]).first()
            if not user:
                print(f"Warning: User '{bet_data['user_username']}' not found, skipping bet...")
                bets_skipped += 1
                imported_bets.append(None)
                continue
            
            # Find team by name
            team = Team.query.filter_by(name=bet_data["team_name"]).first()
            if not team:
                print(f"Warning: Team '{bet_data['team_name']}' not found, skipping bet...")
                bets_skipped += 1
                imported_bets.append(None)
                continue
            
            # Find match - try by ID first, then by teams and league
            match = None
            if bet_data.get("match_id"):
                match = db.session.get(Match, bet_data["match_id"])
            
            if not match and bet_data.get("home_team_name") and bet_data.get("away_team_name"):
                # Try to find by team names
                from app.models import League
                home_team = Team.query.filter_by(name=bet_data["home_team_name"]).first()
                away_team = Team.query.filter_by(name=bet_data["away_team_name"]).first()
                league = League.query.filter_by(name=bet_data.get("league_name")).first() if bet_data.get("league_name") else None
                
                if home_team and away_team:
                    query = Match.query.filter_by(
                        home_team_id=home_team.id,
                        away_team_id=away_team.id
                    )
                    if league:
                        query = query.filter_by(league_id=league.id)
                    match = query.first()
            
            if not match:
                print(f"Warning: Match not found for bet, skipping...")
                bets_skipped += 1
                imported_bets.append(None)
                continue
            
            # Create the appropriate bet type
            if bet_data.get("is_ai_bet"):
                from app.models.bet import AIBet
                bet = AIBet(
                    user_id=user.id,
                    match_id=match.id,
                    team_id=team.id,
                    bet_type=bet_data["bet_type"],
                    target_value=bet_data.get("target_value"),
                    amount=bet_data["amount"],
                    status=bet_data.get("status", "pending"),
                    payout=bet_data.get("payout", 0),
                    placed_at=deserialize_datetime(bet_data.get("placed_at")) or datetime.utcnow(),
                    resolved_at=deserialize_datetime(bet_data.get("resolved_at")),
                    ai_multiplier=bet_data.get("ai_multiplier"),
                    ai_rationale=bet_data.get("ai_rationale"),
                    ai_confidence=bet_data.get("ai_confidence"),
                )
            else:
                bet = Bet(
                    user_id=user.id,
                    match_id=match.id,
                    team_id=team.id,
                    bet_type=bet_data["bet_type"],
                    target_value=bet_data.get("target_value"),
                    amount=bet_data["amount"],
                    status=bet_data.get("status", "pending"),
                    payout=bet_data.get("payout", 0),
                    placed_at=deserialize_datetime(bet_data.get("placed_at")) or datetime.utcnow(),
                    resolved_at=deserialize_datetime(bet_data.get("resolved_at")),
                )
            
            db.session.add(bet)
            db.session.flush()
            imported_bets.append(bet)
            bets_imported += 1
        
        # Import notifications
        notifications_imported = 0
        notifications_skipped = 0
        
        for notification_data in import_data.get("notifications", []):
            # Find user
            user = User.query.filter_by(username=notification_data["user_username"]).first()
            if not user:
                print(f"Warning: User '{notification_data['user_username']}' not found for notification, skipping...")
                notifications_skipped += 1
                continue
            
            # Find the imported bet by index
            bet_index = notification_data.get("bet_index")
            if bet_index is None or bet_index >= len(imported_bets) or imported_bets[bet_index] is None:
                print(f"Warning: Bet not found for notification, skipping...")
                notifications_skipped += 1
                continue
            
            bet = imported_bets[bet_index]
            
            notification = BetNotification(
                user_id=user.id,
                bet_id=bet.id,
                is_read=notification_data.get("is_read", False),
                created_at=deserialize_datetime(notification_data.get("created_at")) or datetime.utcnow(),
                read_at=deserialize_datetime(notification_data.get("read_at")),
            )
            db.session.add(notification)
            notifications_imported += 1
        
        db.session.commit()
        
        print(f"\nImport complete.")
        print(f"Bets imported: {bets_imported}")
        if bets_skipped > 0:
            print(f"Bets skipped: {bets_skipped}")
        print(f"Notifications imported: {notifications_imported}")
        if notifications_skipped > 0:
            print(f"Notifications skipped: {notifications_skipped}")


def main():
    parser = argparse.ArgumentParser(description="Bet export/import utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export bets to JSON")
    export_parser.add_argument(
        "-o", "--output",
        default="backups/bets_export.json",
        help="Output file path (default: backups/bets_export.json)"
    )
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import bets from JSON")
    import_parser.add_argument(
        "-i", "--input",
        default="backups/bets_export.json",
        help="Input file path (default: backups/bets_export.json)"
    )
    import_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset (delete) all existing bets before import"
    )
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_bets(args.output)
    elif args.command == "import":
        import_bets(args.input, reset=args.reset)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
