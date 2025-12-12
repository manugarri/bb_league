# Blood Bowl League Tracker - Makefile
# Use: make <command>

.PHONY: help run dev seed reset clean install test upsert-user

# Default target
help:
	@echo "Blood Bowl League Tracker - Available Commands:"
	@echo ""
	@echo "  make install    - Install dependencies using uv"
	@echo "  make run        - Start the application"
	@echo "  make dev        - Start the application in debug mode"
	@echo "  make seed       - Seed the database with initial data"
	@echo "  make reset      - Reset the database (delete and recreate)"
	@echo "  make clean      - Remove database and cache files"
	@echo "  make test       - Run tests"
	@echo "  make upsert-user USERNAME=<name> [PASSWORD=<pass>] [ADMIN=1]"
	@echo "                  - Create or update a user"
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

# Seed the database
seed:
	uv run python seed.py

# Reset the database (delete and recreate with seed data)
reset:
	@echo "Resetting database..."
	-del /Q instance\*.db 2>nul || rm -f instance/*.db 2>/dev/null || true
	-del /Q *.db 2>nul || rm -f *.db 2>/dev/null || true
	uv run python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all(); print('Database reset complete.')"
	uv run python seed.py
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

