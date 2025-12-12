"""Pytest configuration and fixtures."""
import pytest
from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app("testing")
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def auth_client(app, client):
    """Create authenticated test client."""
    with app.app_context():
        user = User(
            username="testuser",
            email="test@example.com"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        # Login
        client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "password123"
        })
    
    return client

