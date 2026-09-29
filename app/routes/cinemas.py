from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required

cinemas_bp = Blueprint("cinemas", __name__)


@cinemas_bp.get("/")
def get_cinemas():
    db = get_db()
    try:
        rows = db.execute("""
            SELECT c.*, u.name as owner_name,
                   (SELECT COUNT(*) FROM screens s WHERE s.cinema_id=c.cinema_id) as screen_count
            FROM cinemas c JOIN users u ON c.owner_id=u.user_id
            ORDER BY c.name ASC
        """).fetchall()
        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    finally:
        db.close()


@cinemas_bp.get("/<int:cinema_id>")
def get_cinema(cinema_id):
    db = get_db()
    try:
        cinema = db.execute("""
            SELECT c.*, u.name as owner_name FROM cinemas c
            JOIN users u ON c.owner_id=u.user_id WHERE c.cinema_id=?
        """, (cinema_id,)).fetchone()
        if not cinema:
            return jsonify({"success": False, "message": "Cinema not found.", "error": "CINEMA_NOT_FOUND"}), 404

        screens = db.execute("SELECT * FROM screens WHERE cinema_id=?", (cinema_id,)).fetchall()
        result = dict(cinema)
        result["screens"] = [dict(s) for s in screens]
        return jsonify({"success": True, "data": result})
    finally:
        db.close()


@cinemas_bp.post("/")
@login_required
def create_cinema():
    if g.current_user["role"] not in ("CINEMA", "ADMIN"):
        return jsonify({"success": False, "message": "Cinema role required.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    location = (data.get("location") or "").strip()
    if not name or not location:
        return jsonify({"success": False, "message": "name and location are required.", "error": "MISSING_FIELDS"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO cinemas (owner_id, name, location, description) VALUES (?,?,?,?)",
            (g.current_user["user_id"], name, location, data.get("description", ""))
        )
        db.commit()
        cinema = db.execute("SELECT * FROM cinemas WHERE cinema_id=?", (cur.lastrowid,)).fetchone()
        return jsonify({"success": True, "message": "Cinema created.", "data": dict(cinema)}), 201
    finally:
        db.close()
