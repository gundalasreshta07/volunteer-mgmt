from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_db, query, query_one
from utils import volunteer_required

drives_bp = Blueprint("drives", __name__, url_prefix="/drives")


@drives_bp.route("", methods=["GET"])
def list_drives():
    city_id = request.args.get("city_id", type=int)
    ngo_id = request.args.get("ngo_id", type=int)

    sql = """
        SELECT
            d.drive_id,
            d.title,
            d.description,
            d.drive_date,
            d.location,
            d.status,
            d.current_registrations,
            d.max_volunteers,
            n.name AS ngo_name,
            c.name AS city_name
        FROM Drive d
        JOIN NGO n ON n.ngo_id = d.ngo_id
        LEFT JOIN City c ON c.city_id = d.city_id
        WHERE d.status = 'upcoming'
    """
    params = []
    if city_id:
        sql += " AND d.city_id = %s"
        params.append(city_id)
    if ngo_id:
        sql += " AND d.ngo_id = %s"
        params.append(ngo_id)

    sql += " ORDER BY d.drive_date ASC"
    drives = query(sql, tuple(params))
    cities = query("SELECT city_id, name FROM City ORDER BY name")
    ngos = query("SELECT ngo_id, name FROM NGO ORDER BY name")
    return render_template(
        "drives/list.html",
        drives=drives,
        cities=cities,
        ngos=ngos,
        selected_city=city_id,
        selected_ngo=ngo_id,
    )


@drives_bp.route("/<int:drive_id>", methods=["GET"])
def drive_detail(drive_id):
    drive = query_one(
        """
        SELECT
            d.*,
            n.name AS ngo_name,
            n.mission AS ngo_mission,
            c.name AS city_name,
            c.state AS city_state,
            co.name AS coordinator_name
        FROM Drive d
        JOIN NGO n ON n.ngo_id = d.ngo_id
        LEFT JOIN City c ON c.city_id = d.city_id
        LEFT JOIN Coordinator co ON co.coord_id = d.coord_id
        WHERE d.drive_id = %s
        """,
        (drive_id,),
    )
    if not drive:
        flash("Drive not found.", "error")
        return redirect(url_for("drives.list_drives"))

    reg_count = query_one("SELECT COUNT(*) AS c FROM Registration WHERE drive_id=%s", (drive_id,))["c"]
    spots_left = max(drive["max_volunteers"] - reg_count, 0)
    is_registered = False

    if session.get("user_type") == "volunteer":
        existing = query_one(
            "SELECT reg_id FROM Registration WHERE vol_id=%s AND drive_id=%s",
            (session["user_id"], drive_id),
        )
        is_registered = existing is not None

    return render_template(
        "drives/detail.html",
        drive=drive,
        is_registered=is_registered,
        spots_left=spots_left,
        current_registrations=reg_count,
    )


@drives_bp.route("/<int:drive_id>/register", methods=["POST"])
@volunteer_required
def register_drive(drive_id):
    vol_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("CALL RegisterVolunteer(%s, %s, @msg)", (vol_id, drive_id))
        cursor.execute("SELECT @msg AS message")
        msg_row = cursor.fetchone()
        message = msg_row[0] if msg_row and msg_row[0] else "Request processed."
        conn.commit()
    except Exception as exc:
        conn.rollback()
        message = f"Could not register: {exc}"
    finally:
        cursor.close()
        conn.close()

    flash_type = "success" if "successful" in message.lower() else "error"
    flash(message, flash_type)
    return redirect(url_for("drives.drive_detail", drive_id=drive_id))
