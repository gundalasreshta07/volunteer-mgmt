from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from db import execute, query, query_one


def ensure_empty_or_continue(table):
    row = query_one(f"SELECT COUNT(*) AS count_rows FROM {table}")
    return row["count_rows"] == 0


def seed_cities():
    if not ensure_empty_or_continue("City"):
        return
    cities = [
        ("Hyderabad", "Telangana"),
        ("Mumbai", "Maharashtra"),
        ("Delhi", "Delhi"),
        ("Bangalore", "Karnataka"),
    ]
    for name, state in cities:
        execute("INSERT INTO City (name, state) VALUES (%s, %s)", (name, state))


def seed_ngos():
    if not ensure_empty_or_continue("NGO"):
        return
    ngos = [
        ("GreenEarth Foundation", "Environmental conservation and plantation drives.", 4, "contact@greenearth.org"),
        ("Teach For Change", "Education access for underserved students.", 1, "hello@teachforchange.org"),
        ("BloodConnect", "Blood donation awareness and donation camps.", 3, "support@bloodconnect.org"),
    ]
    for ngo in ngos:
        execute(
            "INSERT INTO NGO (name, mission, city_id, contact_email) VALUES (%s, %s, %s, %s)",
            ngo,
        )


def seed_coordinators():
    if not ensure_empty_or_continue("Coordinator"):
        return
    coordinators = [
        ("Anita Rao", "anita@greenearth.org", generate_password_hash("coord123", method="pbkdf2:sha256"), 1),
        ("Rahul Verma", "rahul@teachforchange.org", generate_password_hash("coord123", method="pbkdf2:sha256"), 2),
    ]
    for coord in coordinators:
        execute(
            "INSERT INTO Coordinator (name, email, password_hash, ngo_id) VALUES (%s, %s, %s, %s)",
            coord,
        )


def seed_volunteers():
    if not ensure_empty_or_continue("Volunteer"):
        return
    volunteers = [
        ("Aarav Shah", "aarav@example.com", "9000000001", 1),
        ("Isha Menon", "isha@example.com", "9000000002", 1),
        ("Rohan Gupta", "rohan.g@example.com", "9000000003", 2),
        ("Sneha Iyer", "sneha@example.com", "9000000004", 2),
        ("Vikram Singh", "vikram@example.com", "9000000005", 3),
        ("Neha Jain", "neha@example.com", "9000000006", 3),
        ("Karan Patel", "karan@example.com", "9000000007", 4),
        ("Pooja Nair", "pooja@example.com", "9000000008", 4),
        ("Aditya Kumar", "aditya@example.com", "9000000009", 1),
        ("Meera Joshi", "meera.j@example.com", "9000000010", 2),
    ]
    for name, email, phone, city_id in volunteers:
        execute(
            """
            INSERT INTO Volunteer (name, email, password_hash, phone, city_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, email, generate_password_hash("vol123", method="pbkdf2:sha256"), phone, city_id),
        )


def seed_drives():
    if not ensure_empty_or_continue("Drive"):
        return

    today = date.today()
    drives = [
        (
            "Hussain Sagar Cleanup",
            "Lake cleanup and awareness event.",
            today + timedelta(days=7),
            "Hyderabad",
            1,
            2,
            2,
            80,
            0,
            "upcoming",
        ),
        (
            "Bandra Tree Plantation",
            "Urban plantation with local schools.",
            today + timedelta(days=12),
            "Mumbai",
            2,
            1,
            1,
            100,
            0,
            "upcoming",
        ),
        (
            "Delhi Blood Donation Camp",
            "Community blood donation with partner hospitals.",
            today + timedelta(days=18),
            "Delhi",
            3,
            3,
            None,
            120,
            0,
            "upcoming",
        ),
        (
            "Bangalore Teaching Marathon",
            "Weekend teaching support for classes 6-10.",
            today - timedelta(days=20),
            "Bangalore",
            4,
            2,
            2,
            60,
            0,
            "completed",
        ),
        (
            "Mumbai Beach Restoration",
            "Cleanup and segregation activity.",
            today - timedelta(days=35),
            "Mumbai",
            2,
            1,
            1,
            90,
            0,
            "completed",
        ),
        (
            "Hyderabad Literacy Camp",
            "Support literacy and mentoring activities.",
            today - timedelta(days=50),
            "Hyderabad",
            1,
            2,
            2,
            70,
            0,
            "completed",
        ),
    ]

    for d in drives:
        execute(
            """
            INSERT INTO Drive
            (title, description, drive_date, location, city_id, ngo_id, coord_id, max_volunteers, current_registrations, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            d,
        )


def seed_completed_drive_activity():
    registration_count = query_one("SELECT COUNT(*) AS count_rows FROM Registration")["count_rows"]
    if registration_count > 0:
        return

    # Completed drives are IDs 4, 5, 6 when run on clean DB.
    completed_drive_ids = [4, 5, 6]
    volunteer_ids = [row["vol_id"] for row in query("SELECT vol_id FROM Volunteer ORDER BY vol_id")]

    planned = [
        # (vol_id, drive_id, hours_logged)
        (volunteer_ids[0], completed_drive_ids[0], 4.0),
        (volunteer_ids[0], completed_drive_ids[1], 4.5),
        (volunteer_ids[0], completed_drive_ids[2], 3.0),  # crosses 10 hrs
        (volunteer_ids[1], completed_drive_ids[0], 2.5),
        (volunteer_ids[2], completed_drive_ids[1], 3.0),
        (volunteer_ids[3], completed_drive_ids[2], 5.0),
        (volunteer_ids[4], completed_drive_ids[1], 6.0),
        (volunteer_ids[5], completed_drive_ids[2], 2.0),
        (volunteer_ids[6], completed_drive_ids[0], 4.0),
        (volunteer_ids[7], completed_drive_ids[2], 4.0),
        (volunteer_ids[8], completed_drive_ids[1], 1.5),
        (volunteer_ids[9], completed_drive_ids[0], 2.0),
    ]

    for vol_id, drive_id, hours in planned:
        execute(
            "INSERT INTO Registration (vol_id, drive_id, status) VALUES (%s, %s, 'registered')",
            (vol_id, drive_id),
        )
        reg_id = query_one(
            "SELECT reg_id FROM Registration WHERE vol_id=%s AND drive_id=%s",
            (vol_id, drive_id),
        )["reg_id"]
        execute(
            "INSERT INTO Attendance (reg_id, hours_logged) VALUES (%s, %s)",
            (reg_id, hours),
        )


def run_seed():
    seed_cities()
    seed_ngos()
    seed_coordinators()
    seed_volunteers()
    seed_drives()
    seed_completed_drive_activity()
    print("Seed complete")


if __name__ == "__main__":
    run_seed()
