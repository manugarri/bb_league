"""Basic tests for the application."""


def test_app_exists(app):
    """Test that app is created."""
    assert app is not None


def test_app_is_testing(app):
    """Test that app is in testing mode."""
    assert app.config["TESTING"] is True


def test_home_page(client):
    """Test home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Blood Bowl" in response.data


def test_login_page(client):
    """Test login page loads."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_register_page(client):
    """Test register page loads."""
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Register" in response.data


def test_teams_page(client):
    """Test teams page loads."""
    response = client.get("/teams/")
    assert response.status_code == 200


def test_leagues_page(client):
    """Test leagues page loads."""
    response = client.get("/leagues/")
    assert response.status_code == 200


def test_matches_page(client):
    """Test matches page loads."""
    response = client.get("/matches/")
    assert response.status_code == 200


def test_api_health(client):
    """Test API health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"

