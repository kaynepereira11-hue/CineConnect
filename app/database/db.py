import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "cinema.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('VIEWER', 'FILMMAKER', 'CINEMA', 'ADMIN')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cinemas (
    cinema_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS screens (
    screen_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cinema_id INTEGER NOT NULL REFERENCES cinemas(cinema_id) ON DELETE CASCADE,
    screen_name TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity > 0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seats (
    seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES screens(screen_id) ON DELETE CASCADE,
    seat_number TEXT NOT NULL,
    seat_type TEXT NOT NULL DEFAULT 'STANDARD' CHECK(seat_type IN ('STANDARD', 'PREMIUM', 'VIP')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(screen_id, seat_number)
);

CREATE TABLE IF NOT EXISTS films (
    film_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filmmaker_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    genre TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK(duration > 0),
    poster TEXT,
    status TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK(status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS screenings (
    screening_id INTEGER PRIMARY KEY AUTOINCREMENT,
    film_id INTEGER NOT NULL REFERENCES films(film_id) ON DELETE CASCADE,
    screen_id INTEGER NOT NULL REFERENCES screens(screen_id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    ticket_price REAL NOT NULL CHECK(ticket_price >= 0),
    status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK(status IN ('SCHEDULED', 'CANCELLED', 'COMPLETED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    screening_id INTEGER NOT NULL REFERENCES screenings(screening_id) ON DELETE CASCADE,
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    booking_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(booking_status IN ('PENDING', 'CONFIRMED', 'CANCELLED')),
    payment_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(payment_status IN ('PENDING', 'PAID', 'FAILED')),
    payment_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_seats (
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    seat_id INTEGER NOT NULL REFERENCES seats(seat_id) ON DELETE CASCADE,
    PRIMARY KEY (booking_id, seat_id)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_films_status ON films(status);
CREATE INDEX IF NOT EXISTS idx_films_filmmaker ON films(filmmaker_id);
CREATE INDEX IF NOT EXISTS idx_cinemas_owner ON cinemas(owner_id);
CREATE INDEX IF NOT EXISTS idx_seats_screen ON seats(screen_id);
CREATE INDEX IF NOT EXISTS idx_screenings_date ON screenings(date);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_screening ON bookings(screening_id);
CREATE INDEX IF NOT EXISTS idx_booking_seats_seat ON booking_seats(seat_id);
"""


def get_db():
    """Get a database connection with row_factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Initialize database schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[OK] Database schema initialized at {DB_PATH}")
