from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def home():
    return render_template("index.html")


@pages_bp.get("/login")
def login():
    return render_template("login.html")


@pages_bp.get("/register")
def register():
    return render_template("register.html")


@pages_bp.get("/films/<int:film_id>")
def film_detail(film_id):
    return render_template("film_detail.html", film_id=film_id)


@pages_bp.get("/screenings/<int:screening_id>/seats")
def seat_selection(screening_id):
    return render_template("seat_selection.html", screening_id=screening_id)


@pages_bp.get("/my-bookings")
def my_bookings():
    return render_template("my_bookings.html")


@pages_bp.get("/filmmaker/dashboard")
def filmmaker_dashboard():
    return render_template("filmmaker_dashboard.html")


@pages_bp.get("/cinema/dashboard")
def cinema_dashboard():
    return render_template("cinema_dashboard.html")


@pages_bp.get("/admin/dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")
