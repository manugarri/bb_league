# Blood Bowl League Tracker - Makefile
# Use: make <command>

.PHONY: help run dev seed seed-test reset clean install test upsert-user db-export db-import export-teams import-teams export-users import-users export-leagues import-leagues

# Default target
help:
	@echo "Blood Bowl League Tracker - Available Commands:"
	@echo ""
	@echo "  make install    - Install dependencies using uv"
	@echo "  make run        - Start the application"
	@echo "  make dev        - Start the application in debug mode"
	@echo "  make seed       - Seed the database with initial data"
	@echo "  make seed-test-data  - Seed test data (users, teams, league)"
	@echo "  make reset      - Reset the database (delete and recreate)"
	@echo "  make clean      - Remove database and cache files"
	@echo "  make test       - Run tests"
	@echo "  make upsert-user USERNAME=<name> [PASSWORD=<pass>] [ADMIN=1]"
	@echo "                  - Create or update a user"
	@echo "  make db-export [FILE=<path>]"
	@echo "                  - Export database to JSON (default: backups/db_export.json)"
	@echo "  make db-import [FILE=<path>]"
	@echo "                  - Import database from JSON (default: backups/db_export.json)"
	@echo "  make export-teams [FILE=<path>]"
	@echo "                  - Export teams to JSON (default: backups/teams_export.json)"
	@echo "  make import-teams [FILE=<path>] [RESET=1]"
	@echo "                  - Import teams from JSON (RESET=1 clears existing teams)"
	@echo "  make export-users [FILE=<path>]"
	@echo "                  - Export users to JSON (default: backups/users_export.json)"
	@echo "  make import-users [FILE=<path>] [RESET=1]"
	@echo "                  - Import users from JSON (RESET=1 clears existing users)"
	@echo "  make export-leagues [FILE=<path>]"
	@echo "                  - Export leagues to JSON (default: backups/leagues_export.json)"
	@echo "  make import-leagues [FILE=<path>] [RESET=1]"
	@echo "                  - Import leagues from JSON (RESET=1 clears existing leagues)"
	@echo ""

# Install dependencies
install-prod:
	uv venv
	uv pip install -e .

# Start the application in prod (ubuntu only)
run-prod:
	uv run gunicorn --bind 127.0.0.1:5000 run:gunicorn_app

# local dev is on a windows machine
install-dev:
	uv venv
	uv pip install -e .

# Start in debug mode
run-dev:
	uv run flask run --debug

# Seed the database with game data
seed:
	uv run python scripts/seed.py

# Seed test data (users, teams, league)
# Usage: make seed-test-data [PLAYERS=4] [ADMINS=1] [TEAMS=1] [LEAGUES=1] [ROSTER=4] [IN_PROGRESS=0]
seed-test-data:
	uv run python scripts/seed_test_data.py \
		--n-players $(or $(PLAYERS),6) \
		--n-admin-players $(or $(ADMINS),1) \
		--n-teams-per-player $(or $(TEAMS),1) \
		--n-leagues $(or $(LEAGUES),2) \
		--n-roster-players $(or $(ROSTER),4) \
		--n-leagues-in-progress $(or $(IN_PROGRESS),1)

# Reset the database (delete and recreate with seed data)
reset:
	@echo "Resetting database..."
	-del /Q instance\*.db 2>nul || rm -f instance/*.db 2>/dev/null || true
	-del /Q *.db 2>nul || rm -f *.db 2>/dev/null || true
	uv run python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all(); print('Database reset complete.')"
	uv run python scripts/seed.py
	@echo "Database reset and seeded successfully!"

# Clean up generated files
clean:
	-del /Q instance\*.db 2>nul || rm -f instance/*.db 2>/dev/null || true
	-del /Q *.db 2>nul || rm -f *.db 2>/dev/null || true
	-rmdir /S /Q __pycache__ 2>nul || rm -rf __pycache__ 2>/dev/null || true
	-rmdir /S /Q .pytest_cache 2>nul || rm -rf .pytest_cache 2>/dev/null || true
	-for /D %%d in (app\__pycache__ app\*\__pycache__) do rmdir /S /Q "%%d" 2>nul || find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up generated files."

# Run tests
test:
	uv run pytest -v

# Create or update a user
# Usage: make upsert-user USERNAME=myuser PASSWORD=mypass ADMIN=1
upsert-user:
ifndef USERNAME
	$(error USERNAME is required. Usage: make upsert-user USERNAME=<name> [PASSWORD=<pass>] [ADMIN=1|0])
endif
	@uv run python scripts/upsert_user.py $(USERNAME) \
		$(if $(PASSWORD),--password $(PASSWORD)) \
		$(if $(filter 1 true yes,$(ADMIN)),--admin) \
		$(if $(filter 0 false no,$(ADMIN)),--no-admin)

# Export database to JSON file
# Usage: make db-export [FILE=backups/db_export.json]
db-export:
	uv run python scripts/db_export_import.py export --output $(or $(FILE),backups/db_export.json)

# Import database from JSON file
# Usage: make db-import [FILE=backups/db_export.json]
db-import:
	uv run python scripts/db_export_import.py import --input $(or $(FILE),backups/db_export.json)

# Export teams to JSON file
# Usage: make export-teams [FILE=backups/teams_export.json]
export-teams:
	uv run python scripts/teams_export_import.py export --output $(or $(FILE),backups/teams_export.json)

# Import teams from JSON file
# Usage: make import-teams [FILE=backups/teams_export.json] [RESET=1]
import-teams:
	uv run python scripts/teams_export_import.py import --input $(or $(FILE),backups/teams_export.json) $(if $(filter 1 true yes,$(RESET)),--reset)

# Export users to JSON file
# Usage: make export-users [FILE=backups/users_export.json]
export-users:
	uv run python scripts/users_export_import.py export --output $(or $(FILE),backups/users_export.json)

# Import users from JSON file
# Usage: make import-users [FILE=backups/users_export.json] [RESET=1]
import-users:
	uv run python scripts/users_export_import.py import --input $(or $(FILE),backups/users_export.json) $(if $(filter 1 true yes,$(RESET)),--reset)

# Export leagues to JSON file
# Usage: make export-leagues [FILE=backups/leagues_export.json]
export-leagues:
	uv run python scripts/leagues_export_import.py export --output $(or $(FILE),backups/leagues_export.json)

# Import leagues from JSON file
# Usage: make import-leagues [FILE=backups/leagues_export.json] [RESET=1]
import-leagues:
	uv run python scripts/leagues_export_import.py import --input $(or $(FILE),backups/leagues_export.json) $(if $(filter 1 true yes,$(RESET)),--reset)

