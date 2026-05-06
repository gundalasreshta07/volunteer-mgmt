# Volunteer Management System (Flask + MySQL)

## 1) Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask mysql-connector-python python-dotenv werkzeug
```

## 2) Configure environment variables

Update `.env`:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=volunteer_mgmt
SECRET_KEY=some_random_string
```

## 3) MySQL setup

Make sure MySQL server is running, then run:

```bash
mysql -u root -p < schema.sql
```

This creates the database, tables, indexes, triggers, procedures, and functions.

## 4) Seed sample data

```bash
python3 seed_data.py
```

Expected output:

```text
Seed complete
```

## 5) Start Flask app

```bash
python3 app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Notes

- `db.py` loads credentials from `.env` using `python-dotenv`.
- Passwords are hashed using `werkzeug.security.generate_password_hash`.
