from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required, roles_required

films_bp = Blueprint("films", __name__)


@films_bp.get("/")
def get_films():
    db = get_db()
    try:
        status = (request.args.get("status") or "APPROVED").upper()
        genre = request.args.get("genre")

        query = """
            SELECT f.*, u.name as filmmaker_name
            FROM films f
            JOIN users u ON f.filmmaker_id = u.user_id
            WHERE f.status = ?
        """
        params = [status]
        if genre:
            query += " AND f.genre LIKE ?"
            params.append(f"%{genre}%")
        query += " ORDER BY f.created_at DESC"

        films = [dict(r) for r in db.execute(query, params).fetchall()]
        return jsonify({"success": True, "data": films})
    finally:
        db.close()


@films_bp.get("/filmmaker/mine")
@login_required
def my_films():
    db = get_db()
    try:
        films = db.execute(
            "SELECT * FROM films WHERE filmmaker_id=? ORDER BY created_at DESC",
            (g.current_user["user_id"],)
        ).fetchall()
        return jsonify({"success": True, "data": [dict(f) for f in films]})
    finally:
        db.close()


@films_bp.get("/<int:film_id>")
def get_film(film_id):
    db = get_db()
    try:
        film = db.execute("""
            SELECT f.*, u.name as filmmaker_name, u.email as filmmaker_email
            FROM films f JOIN users u ON f.filmmaker_id=u.user_id
            WHERE f.film_id=?
        """, (film_id,)).fetchone()

        if not film:
            return jsonify({"success": False, "message": "Film not found.", "error": "FILM_NOT_FOUND"}), 404

        screenings = db.execute("""
            SELECT s.*, sc.screen_name, c.name as cinema_name, c.location as cinema_location
            FROM screenings s
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE s.film_id=? AND s.status='SCHEDULED'
            ORDER BY s.date ASC, s.start_time ASC
        """, (film_id,)).fetchall()

        result = dict(film)
        result["screenings"] = [dict(s) for s in screenings]
        return jsonify({"success": True, "data": result})
    finally:
        db.close()


@films_bp.post("/")
@login_required
def create_film():
    if g.current_user["role"] not in ("FILMMAKER", "ADMIN"):
        return jsonify({"success": False, "message": "Only filmmakers can submit films.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    genre = (data.get("genre") or "").strip()
    duration = data.get("duration")

    if not title or not genre or not duration:
        return jsonify({"success": False, "message": "title, genre, and duration are required.", "error": "MISSING_FIELDS"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO films (filmmaker_id, title, description, genre, duration, poster, status) VALUES (?,?,?,?,?,?,?)",
            (g.current_user["user_id"], title, data.get("description", ""),
             genre, int(duration), data.get("poster"), "SUBMITTED")
        )
        db.commit()
        film = db.execute("SELECT * FROM films WHERE film_id=?", (cur.lastrowid,)).fetchone()
        return jsonify({"success": True, "message": "Film submitted for review.", "data": dict(film)}), 201
    finally:
        db.close()


@films_bp.patch("/<int:film_id>/status")
@login_required
def update_film_status(film_id):
    if g.current_user["role"] != "ADMIN":
        return jsonify({"success": False, "message": "Admin access required.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    status = (data.get("status") or "").upper()
    if status not in ("DRAFT", "SUBMITTED", "APPROVED", "REJECTED"):
        return jsonify({"success": False, "message": "Invalid status value.", "error": "INVALID_STATUS"}), 400

    db = get_db()
    try:
        result = db.execute("UPDATE films SET status=? WHERE film_id=?", (status, film_id))
        db.commit()
        if result.rowcount == 0:
            return jsonify({"success": False, "message": "Film not found.", "error": "FILM_NOT_FOUND"}), 404
        return jsonify({"success": True, "message": f"Film status updated to {status}."})
    finally:
        db.close()
