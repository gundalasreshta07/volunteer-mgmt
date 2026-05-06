import os

from dotenv import load_dotenv
from flask import Flask, render_template

from blueprints.admin import admin_bp
from blueprints.auth import auth_bp
from blueprints.drives import drives_bp
from blueprints.volunteer import volunteer_bp
from db import query, query_one


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")

app.register_blueprint(auth_bp)
app.register_blueprint(volunteer_bp)
app.register_blueprint(drives_bp)
app.register_blueprint(admin_bp)


@app.route("/")
def index():
    total_volunteers = query_one("SELECT COUNT(*) AS c FROM Volunteer")["c"]
    total_drives = query_one("SELECT COUNT(*) AS c FROM Drive WHERE status='completed'")["c"]
    total_hours = query_one("SELECT COALESCE(SUM(total_hours), 0) AS c FROM Volunteer")["c"]
    total_ngos = query_one("SELECT COUNT(*) AS c FROM NGO")["c"]

    upcoming_drives = query_one(
        """
        SELECT COUNT(*) AS c FROM Drive
        WHERE status = 'upcoming'
        """
    )["c"]
    recent_upcoming = []
    if upcoming_drives > 0:
        recent_upcoming = query(
            """
            SELECT d.drive_id, d.title, d.drive_date, d.location, n.name AS ngo_name, c.name AS city_name
            FROM Drive d
            JOIN NGO n ON n.ngo_id = d.ngo_id
            LEFT JOIN City c ON c.city_id = d.city_id
            WHERE d.status = 'upcoming'
            ORDER BY d.drive_date ASC
            LIMIT 3
            """
        )

    return render_template(
        "index.html",
        total_volunteers=total_volunteers,
        total_drives=total_drives,
        total_hours=total_hours,
        total_ngos=total_ngos,
        upcoming_drives=recent_upcoming,
    )


if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 5000))
app.run(debug=False, host='0.0.0.0', port=port)
