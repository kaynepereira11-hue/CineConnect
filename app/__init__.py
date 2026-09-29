"""
CineConnect Flask Application Factory
"""

from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "dev_jwt_secret_change_in_production_32chars")
    app.config["JWT_EXPIRES_HOURS"] = int(os.getenv("JWT_EXPIRES_HOURS", 168))
    app.config["RAZORPAY_KEY_ID"] = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    app.config["RAZORPAY_KEY_SECRET"] = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_placeholder_secret")
    app.config["DATABASE_PATH"] = os.getenv("DATABASE_PATH", "app/database/cinema.db")

    # Register all blueprints
    from app.routes.auth import auth_bp
    from app.routes.films import films_bp
    from app.routes.cinemas import cinemas_bp
    from app.routes.screens import screens_bp
    from app.routes.seats import seats_bp
    from app.routes.screenings import screenings_bp
    from app.routes.bookings import bookings_bp
    from app.routes.payments import payments_bp
    from app.routes.users import users_bp
    from app.routes.pages import pages_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(films_bp, url_prefix="/api/films")
    app.register_blueprint(cinemas_bp, url_prefix="/api/cinemas")
    app.register_blueprint(screens_bp, url_prefix="/api/screens")
    app.register_blueprint(seats_bp, url_prefix="/api/seats")
    app.register_blueprint(screenings_bp, url_prefix="/api/screenings")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(pages_bp)  # HTML pages served at root /

    @app.get("/api/health")
    def health():
        from app.database.db import get_db
        try:
            db = get_db()
            db.execute("SELECT 1").fetchone()
            db.close()
            db_status = "CONNECTED"
        except Exception as e:
            db_status = f"ERROR: {str(e)}"
        return {
            "success": True,
            "message": "CineConnect API is healthy.",
            "data": {
                "status": "UP",
                "database": db_status,
                "python_backend": "Flask 3.x + SQLite"
            }
        }

    return app
