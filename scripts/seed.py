#!/usr/bin/env python
"""Script to seed the database with initial data."""
from app import create_app
from app.services.seed_data import seed_all

app = create_app()

with app.app_context():
    seed_all()

