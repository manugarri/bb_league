#!/usr/bin/env python
"""User export and import utilities."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import User


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


def export_users(output_file: str):
    """Export all users to a JSON file."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "users": []
        }
        
        for user in users:
            print(f"Exporting user: {user.username}")
            
            user_data = {
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role,
                "is_active": user.is_active,
                "display_name": user.display_name,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "created_at": serialize_datetime(user.created_at),
                "updated_at": serialize_datetime(user.updated_at)
            }
            
            export_data["users"].append(user_data)
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nUsers exported to: {output_path}")
        print(f"Total users: {len(export_data['users'])}")


def import_users(input_file: str, reset: bool = False):
    """Import users from a JSON file."""
    app = create_app()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    print(f"Importing from: {input_path}")
    print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
    print(f"Mode: {'RESET (clearing existing users)' if reset else 'ADD (adding to existing)'}")
    
    with app.app_context():
        if reset:
            print("\nClearing existing users...")
            # Note: This will cascade delete teams, leagues, etc.
            # Only use if you really want to reset everything
            User.query.delete()
            db.session.commit()
            print("Existing users cleared.")
        
        imported_count = 0
        skipped_count = 0
        updated_count = 0
        
        for user_data in import_data["users"]:
            username = user_data["username"]
            email = user_data["email"]
            
            # Check if user already exists by username or email
            existing_by_username = User.query.filter_by(username=username).first()
            existing_by_email = User.query.filter_by(email=email).first()
            
            if existing_by_username or existing_by_email:
                if not reset:
                    print(f"Skipping user '{username}' - already exists")
                    skipped_count += 1
                    continue
            
            print(f"Importing user: {username}")
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=user_data["password_hash"],
                role=user_data.get("role", "coach"),
                is_active=user_data.get("is_active", True),
                display_name=user_data.get("display_name"),
                bio=user_data.get("bio"),
                avatar_url=user_data.get("avatar_url"),
                created_at=deserialize_datetime(user_data.get("created_at")) or datetime.utcnow(),
                updated_at=deserialize_datetime(user_data.get("updated_at")) or datetime.utcnow()
            )
            db.session.add(user)
            imported_count += 1
        
        db.session.commit()
        
        print(f"\nImport complete.")
        print(f"Users imported: {imported_count}")
        if skipped_count > 0:
            print(f"Users skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="User export/import utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export users to JSON")
    export_parser.add_argument(
        "-o", "--output",
        default="backups/users_export.json",
        help="Output file path (default: backups/users_export.json)"
    )
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import users from JSON")
    import_parser.add_argument(
        "-i", "--input",
        default="backups/users_export.json",
        help="Input file path (default: backups/users_export.json)"
    )
    import_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset (delete) all existing users before import (WARNING: cascades to teams, leagues, etc.)"
    )
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_users(args.output)
    elif args.command == "import":
        import_users(args.input, reset=args.reset)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

