from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import execute, query, query_one

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        cities = query("SELECT city_id, name, state FROM City ORDER BY name")
        return render_template("auth/register.html", cities=cities)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    phone = request.form.get("phone", "").strip()
    city_id = request.form.get("city_id") or None

    if not name or not email or not password:
        flash("Name, email, and password are required.", "error")
        return redirect(url_for("auth.register"))

    try:
        vol_id = execute(
            """
            INSERT INTO Volunteer (name, email, password_hash, phone, city_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, email, generate_password_hash(password, method="pbkdf2:sha256"), phone, city_id),
        )
    except Exception:
        flash("Registration failed. Email may already exist.", "error")
        return redirect(url_for("auth.register"))

    session["user_id"] = vol_id
    session["user_type"] = "volunteer"
    flash("Welcome to VolunteerHub!", "success")
    return redirect(url_for("volunteer.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    volunteer = query_one(
        "SELECT vol_id AS user_id, password_hash FROM Volunteer WHERE email=%s",
        (email,),
    )
    if volunteer and check_password_hash(volunteer["password_hash"], password):
        session["user_id"] = volunteer["user_id"]
        session["user_type"] = "volunteer"
        flash("Logged in successfully.", "success")
        return redirect(url_for("volunteer.dashboard"))

    coordinator = query_one(
        "SELECT coord_id AS user_id, password_hash FROM Coordinator WHERE email=%s",
        (email,),
    )
    if coordinator and check_password_hash(coordinator["password_hash"], password):
        session["user_id"] = coordinator["user_id"]
        session["user_type"] = "coordinator"
        flash("Logged in successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    flash("Invalid email or password.", "error")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
