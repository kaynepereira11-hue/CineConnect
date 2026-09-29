from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required, roles_required, hash_password, verify_password

users_bp = Blueprint("users", __name__)


@users_bp.get("/profile")
@login_required
def get_profile():
    db = get_db()
    try:
        user = db.execute(
            "SELECT user_id, name, email, role, created_at FROM users WHERE user_id=?",
            (g.current_user["user_id"],)
        ).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found.", "error": "USER_NOT_FOUND"}), 404
        return jsonify({"success": True, "data": dict(user)})
    finally:
        db.close()


@users_bp.put("/profile")
@login_required
def update_profile():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE user_id=?", (g.current_user["user_id"],)).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found.", "error": "USER_NOT_FOUND"}), 404

        if name:
            db.execute("UPDATE users SET name=? WHERE user_id=?", (name, g.current_user["user_id"]))

        if new_password:
            if not current_password or not verify_password(current_password, user["password"]):
                return jsonify({"success": False, "message": "Incorrect current password.", "error": "INVALID_PASSWORD"}), 400
            if len(new_password) < 6:
                return jsonify({"success": False, "message": "New password must be at least 6 characters.", "error": "PASSWORD_TOO_SHORT"}), 400
            hashed = hash_password(new_password)
            db.execute("UPDATE users SET password=? WHERE user_id=?", (hashed, g.current_user["user_id"]))

        db.commit()
        updated_user = db.execute(
            "SELECT user_id, name, email, role, created_at FROM users WHERE user_id=?",
            (g.current_user["user_id"],)
        ).fetchone()

        return jsonify({"success": True, "message": "Profile updated successfully.", "data": dict(updated_user)})
    finally:
        db.close()


@users_bp.get("/")
@roles_required("ADMIN")
def list_users():
    db = get_db()
    try:
        users = db.execute("SELECT user_id, name, email, role, created_at FROM users ORDER BY created_at DESC").fetchall()
        return jsonify({"success": True, "data": [dict(u) for u in users]})
    finally:
        db.close()
