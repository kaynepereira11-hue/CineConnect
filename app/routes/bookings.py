import time
from flask import Blueprint, request, jsonify, g
from app.database.db import get_db
from app.auth import login_required

bookings_bp = Blueprint("bookings", __name__)


@bookings_bp.post("/initiate")
@login_required
def initiate_booking():
    if g.current_user["role"] != "VIEWER":
        return jsonify({"success": False, "message": "Only viewers can book tickets.", "error": "FORBIDDEN_ROLE"}), 403

    data = request.get_json() or {}
    screening_id = data.get("screening_id")
    seat_ids = data.get("seat_ids", [])

    if not screening_id or not seat_ids or not isinstance(seat_ids, list):
        return jsonify({"success": False, "message": "screening_id and seat_ids (list) are required.", "error": "INVALID_REQUEST"}), 400

    db = get_db()
    try:
        # --- All validation inside a transaction ---
        db.execute("BEGIN IMMEDIATE")

        screening = db.execute(
            "SELECT * FROM screenings WHERE screening_id=? AND status='SCHEDULED'", (screening_id,)
        ).fetchone()
        if not screening:
            db.execute("ROLLBACK")
            return jsonify({"success": False, "message": "Screening not found or not available.", "error": "SCREENING_NOT_FOUND"}), 404

        # Validate all seat_ids belong to the correct screen
        placeholders = ",".join("?" * len(seat_ids))
        seats = db.execute(
            f"SELECT seat_id, seat_number FROM seats WHERE screen_id=? AND seat_id IN ({placeholders})",
            [screening["screen_id"]] + seat_ids
        ).fetchall()
        if len(seats) != len(seat_ids):
            db.execute("ROLLBACK")
            return jsonify({"success": False, "message": "One or more seat IDs are invalid for this screen.", "error": "INVALID_SEATS"}), 400

        # Check for conflicting bookings (anti double-booking)
        conflict = db.execute(f"""
            SELECT st.seat_number FROM booking_seats bs
            JOIN bookings b ON bs.booking_id=b.booking_id
            JOIN seats st ON bs.seat_id=st.seat_id
            WHERE b.screening_id=? AND b.booking_status IN ('PENDING','CONFIRMED')
            AND bs.seat_id IN ({placeholders})
        """, [screening_id] + seat_ids).fetchall()

        if conflict:
            db.execute("ROLLBACK")
            names = ", ".join(r["seat_number"] for r in conflict)
            return jsonify({"success": False, "message": f"Seat(s) {names} are already reserved.", "error": "SEAT_CONFLICT"}), 409

        # Server-side price calculation (never trust client)
        total_amount = len(seat_ids) * float(screening["ticket_price"])
        order_id = f"order_cc_{int(time.time())}_{g.current_user['user_id']}"

        # Insert booking
        cur = db.execute(
            "INSERT INTO bookings (user_id, screening_id, total_amount, booking_status, payment_status, payment_id) VALUES (?,?,?,'PENDING','PENDING',?)",
            (g.current_user["user_id"], screening_id, total_amount, order_id)
        )
        booking_id = cur.lastrowid

        # Insert booking_seats
        for sid in seat_ids:
            db.execute("INSERT INTO booking_seats (booking_id, seat_id) VALUES (?,?)", (booking_id, sid))

        db.execute("COMMIT")

        return jsonify({
            "success": True,
            "message": "Seats reserved. Proceed to payment.",
            "data": {
                "booking_id": booking_id,
                "razorpay_order_id": order_id,
                "total_amount": total_amount,
                "seats": [r["seat_number"] for r in seats],
                "booking_status": "PENDING"
            }
        }), 201

    except Exception as e:
        db.execute("ROLLBACK")
        raise e
    finally:
        db.close()


@bookings_bp.get("/user/history")
@login_required
def user_history():
    db = get_db()
    try:
        bookings = db.execute("""
            SELECT b.*, s.date as screening_date, s.start_time, s.end_time,
                   f.title as film_title, f.poster as film_poster,
                   sc.screen_name, c.name as cinema_name
            FROM bookings b
            JOIN screenings s ON b.screening_id=s.screening_id
            JOIN films f ON s.film_id=f.film_id
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE b.user_id=?
            ORDER BY b.created_at DESC
        """, (g.current_user["user_id"],)).fetchall()

        results = []
        for b in bookings:
            booking_dict = dict(b)
            seats = db.execute("""
                SELECT st.seat_number FROM booking_seats bs
                JOIN seats st ON bs.seat_id=st.seat_id
                WHERE bs.booking_id=?
            """, (b["booking_id"],)).fetchall()
            booking_dict["seats"] = [s["seat_number"] for s in seats]
            results.append(booking_dict)

        return jsonify({"success": True, "data": results})
    finally:
        db.close()


@bookings_bp.get("/<int:booking_id>")
@login_required
def get_booking(booking_id):
    db = get_db()
    try:
        booking = db.execute("""
            SELECT b.*, u.name as user_name, u.email as user_email,
                   s.date as screening_date, s.start_time, s.end_time, s.ticket_price,
                   f.title as film_title, f.poster as film_poster, f.duration as film_duration,
                   f.genre as film_genre,
                   sc.screen_name, c.name as cinema_name, c.location as cinema_location
            FROM bookings b
            JOIN users u ON b.user_id=u.user_id
            JOIN screenings s ON b.screening_id=s.screening_id
            JOIN films f ON s.film_id=f.film_id
            JOIN screens sc ON s.screen_id=sc.screen_id
            JOIN cinemas c ON sc.cinema_id=c.cinema_id
            WHERE b.booking_id=?
        """, (booking_id,)).fetchone()

        if not booking:
            return jsonify({"success": False, "message": "Booking not found.", "error": "BOOKING_NOT_FOUND"}), 404

        user = g.current_user
        if user["role"] != "ADMIN" and booking["user_id"] != user["user_id"]:
            return jsonify({"success": False, "message": "Unauthorized to view this booking.", "error": "FORBIDDEN"}), 403

        seats = db.execute("""
            SELECT st.seat_id, st.seat_number, st.seat_type
            FROM booking_seats bs JOIN seats st ON bs.seat_id=st.seat_id
            WHERE bs.booking_id=? ORDER BY st.seat_number ASC
        """, (booking_id,)).fetchall()

        result = dict(booking)
        result["seats"] = [dict(s) for s in seats]
        return jsonify({"success": True, "data": result})
    finally:
        db.close()
