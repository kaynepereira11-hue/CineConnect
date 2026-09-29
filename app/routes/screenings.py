from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required

screenings_bp = Blueprint("screenings", __name__)


@screenings_bp.get("/")
def get_screenings():
    db = get_db()
    try:
        params = []
        query = """
            SELECT s.*, f.title as film_title, f.genre as film_genre, f.duration as film_duration,
                   f.poster as film_poster, sc.screen_name,
                   c.name as cinema_name, c.location as cinema_location
            FROM screenings s
            JOIN films f ON s.film_id=f.film_id
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE s.status='SCHEDULED'
        """
        if request.args.get("film_id"):
            query += " AND s.film_id=?"; params.append(request.args["film_id"])
        if request.args.get("cinema_id"):
            query += " AND sc.cinema_id=?"; params.append(request.args["cinema_id"])
        if request.args.get("date"):
            query += " AND s.date=?"; params.append(request.args["date"])
        query += " ORDER BY s.date ASC, s.start_time ASC"

        rows = db.execute(query, params).fetchall()
        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    finally:
        db.close()


@screenings_bp.get("/<int:screening_id>")
def get_screening(screening_id):
    db = get_db()
    try:
        row = db.execute("""
            SELECT s.*, f.title as film_title, f.description as film_description,
                   f.genre as film_genre, f.duration as film_duration, f.poster as film_poster,
                   sc.screen_name, sc.capacity as screen_capacity,
                   c.cinema_id, c.name as cinema_name, c.location as cinema_location
            FROM screenings s
            JOIN films f ON s.film_id=f.film_id
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE s.screening_id=?
        """, (screening_id,)).fetchone()

        if not row:
            return jsonify({"success": False, "message": "Screening not found.", "error": "SCREENING_NOT_FOUND"}), 404
        return jsonify({"success": True, "data": dict(row)})
    finally:
        db.close()


@screenings_bp.post("/")
@login_required
def create_screening():
    if g.current_user["role"] not in ("CINEMA", "ADMIN"):
        return jsonify({"success": False, "message": "Cinema role required.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    required = ["film_id", "screen_id", "date", "start_time", "end_time", "ticket_price"]
    if not all(data.get(k) is not None for k in required):
        return jsonify({"success": False, "message": f"Fields required: {required}", "error": "MISSING_FIELDS"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO screenings (film_id, screen_id, date, start_time, end_time, ticket_price, status) VALUES (?,?,?,?,?,?,'SCHEDULED')",
            (data["film_id"], data["screen_id"], data["date"],
             data["start_time"], data["end_time"], float(data["ticket_price"]))
        )
        db.commit()
        s = db.execute("SELECT * FROM screenings WHERE screening_id=?", (cur.lastrowid,)).fetchone()
        return jsonify({"success": True, "message": "Screening scheduled.", "data": dict(s)}), 201
    finally:
        db.close()
