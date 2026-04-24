import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_NAME = "users.db"

def connect():
    return sqlite3.connect(DB_NAME)

# 🔐 Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- CREATE TABLES ----------------
def create_tables():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        tier TEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_name TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        username TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- USER FUNCTIONS ----------------
def add_user(username, password):
    conn = connect()
    cursor = conn.cursor()

    hashed_pw = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (username, password, tier) VALUES (?, ?, ?)",
            (username, hashed_pw, None)   # No plan selected initially
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass

    conn.close()


def verify_user(username, password):
    conn = connect()
    cursor = conn.cursor()

    hashed_pw = hash_password(password)

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hashed_pw)
    )

    user = cursor.fetchone()
    conn.close()

    return user is not None


def update_last_login(username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=?",
        (username,)
    )

    conn.commit()
    conn.close()


def get_user_tier(username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT tier FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def has_selected_plan(username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT tier FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()

    return result and result[0] is not None


# ---------------- API LOGGING ----------------
def log_api_call(api_name, username):
    conn = connect()
    cursor = conn.cursor()

    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO api_requests (api_name, username, timestamp) VALUES (?, ?, ?)",
        (api_name, username, local_time)
    )

    conn.commit()
    conn.close()


def get_api_usage(api_name, time_window, username):
    conn = connect()
    cursor = conn.cursor()

    cutoff_time = (datetime.now() - timedelta(seconds=time_window)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    SELECT COUNT(*) FROM api_requests
    WHERE api_name=? AND username=?
    AND timestamp >= ?
    """, (api_name, username, cutoff_time))

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_earliest_request_time(api_name, time_window, username):
    conn = connect()
    cursor = conn.cursor()

    cutoff_time = (datetime.now() - timedelta(seconds=time_window)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    SELECT MIN(timestamp) FROM api_requests
    WHERE api_name=? AND username=?
    AND timestamp >= ?
    """, (api_name, username, cutoff_time))

    result = cursor.fetchone()[0]
    conn.close()

    return result