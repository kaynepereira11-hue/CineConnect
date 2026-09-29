from flask import Blueprint, request, jsonify
from app.database.db import get_db

seats_bp = Blueprint("seats", __name__)


@seats_bp.get("/screen/<int:screen_id>")
def get_seats_by_screen(screen_id):
    db = get_db()
    try:
        seats = db.execute(
            "SELECT * FROM seats WHERE screen_id=? ORDER BY seat_number ASC", (screen_id,)
        ).fetchall()
        return jsonify({"success": True, "data": [dict(s) for s in seats]})
    finally:
        db.close()


@seats_bp.get("/screening/<int:screening_id>")
def get_seats_for_screening(screening_id):
    db = get_db()
    try:
        screening = db.execute("""
            SELECT s.*, f.title as film_title, sc.screen_name, sc.screen_id,
                   c.name as cinema_name, c.location as cinema_location
            FROM screenings s
            JOIN films f ON s.film_id=f.film_id
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE s.screening_id=?
        """, (screening_id,)).fetchone()

        if not screening:
            return jsonify({"success": False, "message": "Screening not found.", "error": "SCREENING_NOT_FOUND"}), 404

        # Return all physical seats, marked as booked if reserved in PENDING or CONFIRMED bookings
        seats = db.execute("""
            SELECT st.seat_id, st.screen_id, st.seat_number, st.seat_type,
                   CASE WHEN bs.seat_id IS NOT NULL THEN 1 ELSE 0 END AS is_booked
            FROM seats st
            LEFT JOIN (
                SELECT DISTINCT bs2.seat_id
                FROM booking_seats bs2
                JOIN bookings b ON bs2.booking_id=b.booking_id
                WHERE b.screening_id=? AND b.booking_status IN ('PENDING','CONFIRMED')
            ) bs ON st.seat_id=bs.seat_id
            WHERE st.screen_id=?
            ORDER BY st.seat_number ASC
        """, (screening_id, screening["screen_id"])).fetchall()

        return jsonify({
            "success": True,
            "data": {
                "screening": dict(screening),
                "seats": [{**dict(s), "is_booked": bool(s["is_booked"])} for s in seats]
            }
        })
    finally:
        db.close()
