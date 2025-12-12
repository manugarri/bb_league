"""Application entry point."""
from app import create_app



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
else:
    #its running on gunicorn
    gunicorn_app = create_app()