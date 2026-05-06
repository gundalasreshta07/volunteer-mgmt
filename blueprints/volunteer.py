from flask import Blueprint, flash, redirect, render_template, session, url_for

from db import execute, query, query_one
from utils import volunteer_required

volunteer_bp = Blueprint("volunteer", __name__, url_prefix="/volunteer")


@volunteer_bp.route("/dashboard")
@volunteer_required
def dashboard():
    vol_id = session["user_id"]
    volunteer = query_one(
        """
        SELECT v.vol_id, v.name, v.email, v.phone, v.total_hours, v.city_id, c.name AS city_name
        FROM Volunteer v
        LEFT JOIN City c ON c.city_id = v.city_id
        WHERE v.vol_id = %s
        """,
        (vol_id,),
    )

    upcoming_drives = query(
        """
        SELECT r.reg_id, d.drive_id, d.title, d.drive_date, d.location, r.status
        FROM Registration r
        JOIN Drive d ON d.drive_id = r.drive_id
        WHERE r.vol_id = %s
          AND r.status = 'registered'
          AND d.status = 'upcoming'
        ORDER BY d.drive_date ASC
        """,
        (vol_id,),
    )

    past_drives = query(
        """
        SELECT d.title, d.drive_date, a.hours_logged
        FROM Registration r
        JOIN Drive d ON d.drive_id = r.drive_id
        JOIN Attendance a ON a.reg_id = r.reg_id
        WHERE r.vol_id = %s
          AND r.status = 'attended'
        ORDER BY d.drive_date DESC
        """,
        (vol_id,),
    )

    certificate = query_one(
        """
        SELECT * FROM Certificate
        WHERE vol_id = %s
        ORDER BY issued_date DESC
        LIMIT 1
        """,
        (vol_id,),
    )

    my_rank = query_one(
        "SELECT GetVolunteerRank(vol_id, city_id) AS my_rank FROM Volunteer WHERE vol_id = %s",
        (vol_id,),
    )
    my_rank = my_rank["my_rank"] if my_rank else None

    leaderboard = query(
        """
        SELECT name, email, total_hours, vol_id
        FROM Volunteer
        WHERE city_id = %s
        ORDER BY total_hours DESC, name ASC
        LIMIT 10
        """,
        (volunteer["city_id"],),
    ) if volunteer else []

    skills = query(
        """
        SELECT s.name, s.category, vs.proficiency_level
        FROM VolunteerSkill vs
        JOIN Skill s ON s.skill_id = vs.skill_id
        WHERE vs.vol_id = %s
        ORDER BY s.name
        """,
        (vol_id,),
    )

    milestones = [10, 25, 50]
    total_hours = volunteer["total_hours"] if volunteer else 0
    next_milestone = next((m for m in milestones if total_hours < m), 50)
    progress_pct = int(min((total_hours / next_milestone) * 100, 100)) if next_milestone else 100

    return render_template(
        "volunteer/dashboard.html",
        volunteer=volunteer,
        upcoming_drives=upcoming_drives,
        past_drives=past_drives,
        certificate=certificate,
        my_rank=my_rank,
        leaderboard=leaderboard,
        skills=skills,
        milestones=milestones,
        next_milestone=next_milestone,
        progress_pct=progress_pct,
    )


@volunteer_bp.route("/cancel/<int:reg_id>", methods=["POST"])
@volunteer_required
def cancel_registration(reg_id):
    vol_id = session["user_id"]
    reg = query_one(
        "SELECT drive_id, status FROM Registration WHERE reg_id=%s AND vol_id=%s",
        (reg_id, vol_id),
    )
    if not reg:
        flash("Registration not found.", "error")
        return redirect(url_for("volunteer.dashboard"))

    if reg["status"] == "cancelled":
        flash("Registration already cancelled.", "error")
        return redirect(url_for("volunteer.dashboard"))

    execute(
        "UPDATE Registration SET status='cancelled' WHERE reg_id=%s AND vol_id=%s",
        (reg_id, vol_id),
    )
    execute(
        """
        UPDATE Drive
        SET current_registrations = GREATEST(current_registrations - 1, 0)
        WHERE drive_id = %s
        """,
        (reg["drive_id"],),
    )
    flash("Registration cancelled", "success")
    return redirect(url_for("volunteer.dashboard"))
