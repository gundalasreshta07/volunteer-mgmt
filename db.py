import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


load_dotenv()


def get_db():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "volunteer_mgmt"),
        )
    except Error as exc:
        print(f"Could not connect to MySQL. Please check your .env credentials. Details: {exc}")
        raise


def query(sql, params=None):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def query_one(sql, params=None):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def execute(sql, params=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.lastrowid
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# Backward-compatible aliases for existing app imports.
fetch_all = query
fetch_one = query_one
execute_commit = execute


def call_procedure(proc_name, args):
    conn = get_db()
    cursor = conn.cursor()
    try:
        result = cursor.callproc(proc_name, args)
        conn.commit()
        return result
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
