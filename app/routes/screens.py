from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required

screens_bp = Blueprint("screens", __name__)


@screens_bp.get("/cinema/<int:cinema_id>")
def get_screens(cinema_id):
    db = get_db()
    try:
        screens = db.execute("""
            SELECT s.*, (SELECT COUNT(*) FROM seats st WHERE st.screen_id=s.screen_id) as total_seats
            FROM screens s WHERE s.cinema_id=? ORDER BY s.screen_name ASC
        """, (cinema_id,)).fetchall()
        return jsonify({"success": True, "data": [dict(s) for s in screens]})
    finally:
        db.close()


@screens_bp.post("/")
@login_required
def create_screen():
    if g.current_user["role"] not in ("CINEMA", "ADMIN"):
        return jsonify({"success": False, "message": "Cinema role required.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    cinema_id = data.get("cinema_id")
    screen_name = (data.get("screen_name") or "").strip()
    capacity = data.get("capacity")

    if not cinema_id or not screen_name or not capacity:
        return jsonify({"success": False, "message": "cinema_id, screen_name and capacity are required.", "error": "MISSING_FIELDS"}), 400

    db = get_db()
    try:
        cur = db.execute("INSERT INTO screens (cinema_id, screen_name, capacity) VALUES (?,?,?)",
                         (cinema_id, screen_name, int(capacity)))
        db.commit()
        screen = db.execute("SELECT * FROM screens WHERE screen_id=?", (cur.lastrowid,)).fetchone()
        return jsonify({"success": True, "message": "Screen created.", "data": dict(screen)}), 201
    finally:
        db.close()
