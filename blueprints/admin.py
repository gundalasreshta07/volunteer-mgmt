from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import execute, get_db, query, query_one
from utils import coordinator_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@coordinator_required
def dashboard():
    coord = query_one(
        "SELECT coord_id, name, ngo_id FROM Coordinator WHERE coord_id = %s",
        (session["user_id"],),
    )
    ngo = query_one(
        "SELECT ngo_id, name, mission, contact_email FROM NGO WHERE ngo_id = %s",
        (coord["ngo_id"],),
    ) if coord else None

    drives = query(
        """
        SELECT
            d.drive_id,
            d.title,
            d.drive_date,
            d.status,
            d.current_registrations AS registered_count,
            COALESCE(att.attended_count, 0) AS attended_count
        FROM Drive d
        LEFT JOIN (
            SELECT r.drive_id, COUNT(*) AS attended_count
            FROM Registration r
            WHERE r.status = 'attended'
            GROUP BY r.drive_id
        ) att ON att.drive_id = d.drive_id
        WHERE d.ngo_id = %s
        ORDER BY drive_date DESC
        """,
        (coord["ngo_id"],),
    ) if coord else []

    today = date.today()
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    impact_report = []
    try:
        cursor.execute("CALL GetNGOImpactReport(%s, %s, %s)", (coord["ngo_id"], today.month, today.year))
        impact_report = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    top_volunteers = query(
        """
        SELECT v.name, v.email, COUNT(r.reg_id) AS drives_attended,
               SUM(a.hours_logged) AS total_hours
        FROM Volunteer v
        JOIN Registration r ON v.vol_id = r.vol_id
        JOIN Attendance a ON r.reg_id = a.reg_id
        JOIN Drive d ON r.drive_id = d.drive_id
        WHERE d.ngo_id = %s AND r.status = 'attended'
        GROUP BY v.vol_id
        ORDER BY total_hours DESC
        LIMIT 10
        """,
        (coord["ngo_id"],),
    )

    month_totals = {"total_drives": 0, "total_volunteers": 0, "total_hours": 0}
    if impact_report:
        month_totals["total_drives"] = len(impact_report)
        month_totals["total_volunteers"] = sum((row["volunteers_attended"] or 0) for row in impact_report)
        month_totals["total_hours"] = sum((row["total_hours_contributed"] or 0) for row in impact_report)

    return render_template(
        "admin/dashboard.html",
        coordinator=coord,
        ngo=ngo,
        drives=drives,
        impact_report=impact_report,
        top_volunteers=top_volunteers,
        month_totals=month_totals,
    )


@admin_bp.route("/drives/create", methods=["GET", "POST"])
@coordinator_required
def create_drive():
    coord = query_one(
        "SELECT coord_id, ngo_id FROM Coordinator WHERE coord_id = %s",
        (session["user_id"],),
    )
    if request.method == "GET":
        cities = query("SELECT city_id, name, state FROM City ORDER BY name")
        return render_template("admin/drives.html", cities=cities)

    title = request.form.get("title", "").strip()
    drive_date = request.form.get("drive_date")
    if not title or not drive_date:
        flash("Title and date are required.", "error")
        return redirect(url_for("admin.create_drive"))

    execute(
        """
        INSERT INTO Drive (
            title, description, drive_date, location, city_id, ngo_id, coord_id, max_volunteers
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            title,
            request.form.get("description"),
            drive_date,
            request.form.get("location"),
            request.form.get("city_id") or None,
            coord["ngo_id"],
            coord["coord_id"],
            request.form.get("max_volunteers", type=int) or 50,
        ),
    )
    flash("Drive created successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/drives/<int:drive_id>/attendance", methods=["GET"])
@coordinator_required
def manage_attendance(drive_id):
    coord = query_one("SELECT ngo_id FROM Coordinator WHERE coord_id=%s", (session["user_id"],))
    drive = query_one(
        "SELECT drive_id, title, ngo_id FROM Drive WHERE drive_id=%s",
        (drive_id,),
    )
    if not drive or drive["ngo_id"] != coord["ngo_id"]:
        flash("Drive not found.", "error")
        return redirect(url_for("admin.dashboard"))

    registrations = query(
        """
        SELECT
            r.reg_id,
            r.status,
            v.name AS volunteer_name,
            v.email AS volunteer_email,
            a.hours_logged
        FROM Registration r
        JOIN Volunteer v ON v.vol_id = r.vol_id
        LEFT JOIN Attendance a ON a.reg_id = r.reg_id
        WHERE r.drive_id = %s
        ORDER BY r.registered_at DESC
        """,
        (drive_id,),
    )
    return render_template("admin/attendance.html", drive=drive, registrations=registrations)


@admin_bp.route("/attendance/log", methods=["POST"])
@coordinator_required
def log_attendance():
    reg_id = request.form.get("reg_id", type=int)
    hours_logged = request.form.get("hours_logged", type=float)
    drive_id = request.form.get("drive_id", type=int)
    if not reg_id or hours_logged is None or not drive_id:
        flash("Invalid attendance submission.", "error")
        return redirect(url_for("admin.dashboard"))

    execute(
        "INSERT INTO Attendance (reg_id, hours_logged) VALUES (%s, %s)",
        (reg_id, hours_logged),
    )
    flash("Attendance logged — hours updated", "success")
    return redirect(url_for("admin.manage_attendance", drive_id=drive_id))


@admin_bp.route("/drives/<int:drive_id>/complete", methods=["POST"])
@coordinator_required
def complete_drive(drive_id):
    coord = query_one("SELECT ngo_id FROM Coordinator WHERE coord_id=%s", (session["user_id"],))
    execute(
        "UPDATE Drive SET status='completed' WHERE drive_id=%s AND ngo_id=%s",
        (drive_id, coord["ngo_id"]),
    )
    flash("Drive marked as completed", "success")
    return redirect(url_for("admin.dashboard"))
