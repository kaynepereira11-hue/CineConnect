"""
Database initialization and seed script.
Run: python -m app.database.init_db
"""

import hashlib, sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.db import get_db, init_db
from werkzeug.security import generate_password_hash
from datetime import date, timedelta

def seed():
    print("🔄 Initializing CineConnect database...")
    init_db()

    conn = get_db()
    try:
        hashed = generate_password_hash("Password123!")

        # Seed users (INSERT OR IGNORE to be idempotent)
        conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?,?,?,?)",
                     ("Aditya Viewer", "viewer@example.com", hashed, "VIEWER"))
        conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?,?,?,?)",
                     ("Priya Filmmaker", "filmmaker@example.com", hashed, "FILMMAKER"))
        conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?,?,?,?)",
                     ("Rohan Cinema Manager", "cinema@example.com", hashed, "CINEMA"))
        conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?,?,?,?)",
                     ("Admin Supervisor", "admin@example.com", hashed, "ADMIN"))
        conn.commit()

        filmmaker = conn.execute("SELECT user_id FROM users WHERE email='filmmaker@example.com'").fetchone()
        cinema_owner = conn.execute("SELECT user_id FROM users WHERE email='cinema@example.com'").fetchone()
        viewer = conn.execute("SELECT user_id FROM users WHERE email='viewer@example.com'").fetchone()

        # Seed cinema
        existing_cinema = conn.execute("SELECT cinema_id FROM cinemas WHERE owner_id=?", (cinema_owner["user_id"],)).fetchone()
        if not existing_cinema:
            cur = conn.execute(
                "INSERT INTO cinemas (owner_id, name, location, description) VALUES (?,?,?,?)",
                (cinema_owner["user_id"], "Starlight Indie Playhouse",
                 "42 Film City Road, Arts Quarter",
                 "A cozy 60-seat arthouse cinema dedicated to independent and student film debuts.")
            )
            cinema_id = cur.lastrowid
        else:
            cinema_id = existing_cinema["cinema_id"]

        # Seed screen
        existing_screen = conn.execute("SELECT screen_id FROM screens WHERE cinema_id=? AND screen_name=?",
                                       (cinema_id, "Screen 1 - Velvet Hall")).fetchone()
        if not existing_screen:
            cur = conn.execute("INSERT INTO screens (cinema_id, screen_name, capacity) VALUES (?,?,?)",
                               (cinema_id, "Screen 1 - Velvet Hall", 30))
            screen_id = cur.lastrowid
        else:
            screen_id = existing_screen["screen_id"]

        # Seed seats (Rows A, B = STANDARD; Row C = PREMIUM)
        seat_count = conn.execute("SELECT COUNT(*) as c FROM seats WHERE screen_id=?", (screen_id,)).fetchone()["c"]
        if seat_count == 0:
            for row in ["A", "B"]:
                for i in range(1, 11):
                    conn.execute("INSERT OR IGNORE INTO seats (screen_id, seat_number, seat_type) VALUES (?,?,?)",
                                 (screen_id, f"{row}{i}", "STANDARD"))
            for i in range(1, 11):
                conn.execute("INSERT OR IGNORE INTO seats (screen_id, seat_number, seat_type) VALUES (?,?,?)",
                             (screen_id, f"C{i}", "PREMIUM"))

        # Seed films
        existing_film = conn.execute("SELECT film_id FROM films WHERE title=?", ("Echoes of Silence",)).fetchone()
        if not existing_film:
            cur1 = conn.execute(
                "INSERT INTO films (filmmaker_id, title, description, genre, duration, poster, status) VALUES (?,?,?,?,?,?,?)",
                (filmmaker["user_id"], "Echoes of Silence",
                 "A haunting psychological drama exploring the unspoken grief of an estranged classical pianist.",
                 "Drama", 42,
                 "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=600&q=80",
                 "APPROVED")
            )
            film1_id = cur1.lastrowid

            cur2 = conn.execute(
                "INSERT INTO films (filmmaker_id, title, description, genre, duration, poster, status) VALUES (?,?,?,?,?,?,?)",
                (filmmaker["user_id"], "Neon Horizon",
                 "In a rain-drenched cyberpunk metropolis, a courier uncovers a clandestine AI conspiracy.",
                 "Sci-Fi", 35,
                 "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
                 "APPROVED")
            )
            film2_id = cur2.lastrowid

            conn.execute(
                "INSERT INTO films (filmmaker_id, title, description, genre, duration, poster, status) VALUES (?,?,?,?,?,?,?)",
                (filmmaker["user_id"], "The Last Reel",
                 "A nostalgic retrospective on vanishing film projectionists in single-screen theatres.",
                 "Documentary", 52,
                 "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=600&q=80",
                 "SUBMITTED")
            )
        else:
            film1_id = existing_film["film_id"]
            film2 = conn.execute("SELECT film_id FROM films WHERE title=?", ("Neon Horizon",)).fetchone()
            film2_id = film2["film_id"] if film2 else film1_id

        # Seed screenings
        scr_count = conn.execute("SELECT COUNT(*) as c FROM screenings").fetchone()["c"]
        if scr_count == 0:
            tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            cur = conn.execute(
                "INSERT INTO screenings (film_id, screen_id, date, start_time, end_time, ticket_price, status) VALUES (?,?,?,?,?,?,?)",
                (film1_id, screen_id, tomorrow, "18:00", "19:30", 150.0, "SCHEDULED")
            )
            screening1_id = cur.lastrowid
            conn.execute(
                "INSERT INTO screenings (film_id, screen_id, date, start_time, end_time, ticket_price, status) VALUES (?,?,?,?,?,?,?)",
                (film2_id, screen_id, tomorrow, "20:00", "21:15", 180.0, "SCHEDULED")
            )
        else:
            screening1_id = conn.execute("SELECT screening_id FROM screenings LIMIT 1").fetchone()["screening_id"]

        # Seed 1 confirmed booking for viewer (seats A1 & A2)
        booking_count = conn.execute("SELECT COUNT(*) as c FROM bookings").fetchone()["c"]
        if booking_count == 0:
            seat_a1 = conn.execute("SELECT seat_id FROM seats WHERE screen_id=? AND seat_number='A1'", (screen_id,)).fetchone()
            seat_a2 = conn.execute("SELECT seat_id FROM seats WHERE screen_id=? AND seat_number='A2'", (screen_id,)).fetchone()
            if seat_a1 and seat_a2:
                cur = conn.execute(
                    "INSERT INTO bookings (user_id, screening_id, total_amount, booking_status, payment_status, payment_id) VALUES (?,?,?,?,?,?)",
                    (viewer["user_id"], screening1_id, 300.0, "CONFIRMED", "PAID", "pay_seed_sample_12345")
                )
                bid = cur.lastrowid
                conn.execute("INSERT INTO booking_seats (booking_id, seat_id) VALUES (?,?)", (bid, seat_a1["seat_id"]))
                conn.execute("INSERT INTO booking_seats (booking_id, seat_id) VALUES (?,?)", (bid, seat_a2["seat_id"]))

        conn.commit()

        # Summary
        print("\n📊 Database Summary:")
        for tbl in ["users", "cinemas", "screens", "seats", "films", "screenings", "bookings"]:
            c = conn.execute(f"SELECT COUNT(*) as n FROM {tbl}").fetchone()["n"]
            print(f"  {tbl}: {c} records")

        print("\n✨ CineConnect database ready!")
        print("\n🔑 Demo Accounts (all password: Password123!)")
        print("  viewer@example.com     → VIEWER")
        print("  filmmaker@example.com  → FILMMAKER")
        print("  cinema@example.com     → CINEMA")
        print("  admin@example.com      → ADMIN")

    finally:
        conn.close()


if __name__ == "__main__":
    seed()
