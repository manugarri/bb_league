#!/usr/bin/env python
"""Script to create or update a user in the Blood Bowl League Tracker."""
import argparse
import sys
from app import create_app
from app.extensions import db
from app.models import User


def upsert_user(username: str, password: str = None, is_admin: bool = None) -> dict:
    """
    Create or update a user.
    
    Args:
        username: The username (required)
        password: The password (optional, only set if provided)
        is_admin: Whether user is admin (optional, only set if provided)
    
    Returns:
        dict with 'action' ('created' or 'updated') and 'user' info
    """
    user = User.query.filter_by(username=username).first()
    
    if user:
        # Update existing user
        updates = []
        
        if password is not None:
            user.set_password(password)
            updates.append("password")
        
        if is_admin is not None:
            user.role = "admin" if is_admin else "coach"
            updates.append(f"role={'admin' if is_admin else 'coach'}")
        
        if updates:
            db.session.commit()
            return {
                "action": "updated",
                "username": username,
                "updates": updates
            }
        else:
            return {
                "action": "no_changes",
                "username": username,
                "message": "No updates provided"
            }
    else:
        # Create new user
        if password is None:
            raise ValueError("Password is required when creating a new user")
        
        # Generate email from username if not provided
        email = f"{username}@bloodbowl.local"
        
        user = User(
            username=username,
            email=email,
            role="admin" if is_admin else "coach"
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return {
            "action": "created",
            "username": username,
            "email": email,
            "role": user.role
        }


def main():
    parser = argparse.ArgumentParser(
        description="Create or update a user in the Blood Bowl League Tracker"
    )
    parser.add_argument(
        "username",
        type=str,
        help="Username (required)"
    )
    parser.add_argument(
        "--password", "-p",
        type=str,
        default=None,
        help="Password (required for new users, optional for updates)"
    )
    parser.add_argument(
        "--admin", "-a",
        action="store_true",
        default=None,
        help="Set user as admin"
    )
    parser.add_argument(
        "--no-admin",
        action="store_true",
        help="Remove admin privileges"
    )
    
    args = parser.parse_args()
    
    # Determine is_admin value
    is_admin = False
    if args.admin:
        is_admin = True
    elif args.no_admin:
        is_admin = False
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            result = upsert_user(
                username=args.username,
                password=args.password,
                is_admin=is_admin
            )
            
            if result["action"] == "created":
                print(f"[OK] Created user '{result['username']}'")
                print(f"     Email: {result['email']}")
                print(f"     Role: {result['role']}")
            elif result["action"] == "updated":
                print(f"[OK] Updated user '{result['username']}'")
                print(f"     Changes: {', '.join(result['updates'])}")
            else:
                print(f"[--] No changes made to user '{result['username']}'")
                print(f"     {result['message']}")
                
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

