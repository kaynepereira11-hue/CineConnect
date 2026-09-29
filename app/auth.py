"""
Authentication helpers: JWT creation/verification and bcrypt password hashing.
"""

import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.db import get_db


def hash_password(plain: str) -> str:
    return generate_password_hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


def create_token(user_id: int, role: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(
            hours=current_app.config["JWT_EXPIRES_HOURS"]
        )
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])


def login_required(f):
    """Decorator: requires a valid JWT in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Authentication token missing.", "error": "AUTH_MISSING"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired.", "error": "TOKEN_EXPIRED"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token.", "error": "INVALID_TOKEN"}), 403

        db = get_db()
        user = db.execute(
            "SELECT user_id, name, email, role, created_at FROM users WHERE user_id=?",
            (payload["user_id"],)
        ).fetchone()
        db.close()

        if not user:
            return jsonify({"success": False, "message": "User account no longer exists.", "error": "USER_NOT_FOUND"}), 401

        g.current_user = dict(user)
        return f(*args, **kwargs)
    return decorated


def roles_required(*allowed_roles):
    """Decorator: requires login_required AND a specific role."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if g.current_user["role"] not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": f"Role '{g.current_user['role']}' is not permitted. Required: {list(allowed_roles)}",
                    "error": "FORBIDDEN_ROLE"
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
