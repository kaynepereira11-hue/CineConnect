from flask import Blueprint, request, jsonify
from app.database.db import get_db
from app.auth import hash_password, verify_password, create_token, login_required
import re

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"VIEWER", "FILMMAKER", "CINEMA", "ADMIN"}


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").upper()

    if not all([name, email, password, role]):
        return jsonify({"success": False, "message": "name, email, password, and role are all required.", "error": "MISSING_FIELDS"}), 400

    if role not in VALID_ROLES:
        return jsonify({"success": False, "message": f"Invalid role. Choose from: {', '.join(VALID_ROLES)}", "error": "INVALID_ROLE"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long.", "error": "PASSWORD_TOO_SHORT"}), 400

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"success": False, "message": "Please provide a valid email address.", "error": "INVALID_EMAIL"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT user_id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return jsonify({"success": False, "message": "An account with this email already exists.", "error": "EMAIL_EXISTS"}), 409

        hashed = hash_password(password)
        cur = db.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                         (name, email, hashed, role))
        db.commit()
        user_id = cur.lastrowid
        token = create_token(user_id, role, email)

        return jsonify({
            "success": True,
            "message": "Registration successful.",
            "data": {"token": token, "user": {"user_id": user_id, "name": name, "email": email, "role": role}}
        }), 201
    finally:
        db.close()


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required.", "error": "MISSING_CREDENTIALS"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not verify_password(password, user["password"]):
            return jsonify({"success": False, "message": "Invalid email or password.", "error": "INVALID_CREDENTIALS"}), 401

        token = create_token(user["user_id"], user["role"], user["email"])
        return jsonify({
            "success": True,
            "message": "Login successful.",
            "data": {
                "token": token,
                "user": {
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                    "created_at": user["created_at"]
                }
            }
        })
    finally:
        db.close()


@auth_bp.get("/me")
@login_required
def me():
    from flask import g
    return jsonify({"success": True, "data": {"user": g.current_user}})
