"""API Blueprint."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health_check():
    """API health check endpoint."""
    return jsonify({"status": "healthy", "message": "Blood Bowl League Tracker API"})


# Import API routes
from app.blueprints.api import teams, leagues, matches


@api_bp.route("/me")
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    from app.models import User
    
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.get_display_name(),
        "role": user.role
    })

