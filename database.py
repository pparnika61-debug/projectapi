import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_NAME = "users.db"

def connect():
    return sqlite3.connect(DB_NAME)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        tier TEXT DEFAULT 'free',
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


# ---------------- USER ----------------
def add_user(username, password):
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, tier) VALUES (?, ?, 'free')",
            (username, hash_password(password))
        )
        conn.commit()
    except:
        pass
    conn.close()

def verify_user(username, password):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return user is not None

def update_last_login(username):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=?", (username,))
    conn.commit()
    conn.close()

def get_user_tier(username):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT tier FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else "free"


# ---------------- API LOGGING ----------------
def log_api_call(api_name, username):
    conn = connect()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO api_requests (api_name, username, timestamp) VALUES (?, ?, ?)",
        (api_name, username, now)
    )

    conn.commit()
    conn.close()


# ---------------- FIXED USAGE CALCULATION ----------------
def get_api_usage(api_name, window, username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp FROM api_requests
    WHERE api_name=? AND username=?
    """, (api_name, username))

    rows = cursor.fetchall()
    now = datetime.now()

    count = 0
    for row in rows:
        req_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if (now - req_time).total_seconds() <= window:
            count += 1

    conn.close()
    return count


def get_previous_window_usage(api_name, window, username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp FROM api_requests
    WHERE api_name=? AND username=?
    """, (api_name, username))

    rows = cursor.fetchall()
    now = datetime.now()

    count = 0
    for row in rows:
        req_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")

        diff = (now - req_time).total_seconds()

        if window < diff <= window * 2:
            count += 1

    conn.close()
    return count


# ---------------- FIXED TIMER ----------------
def get_earliest_request_time(api_name, window, username):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp FROM api_requests
    WHERE api_name=? AND username=?
    ORDER BY timestamp ASC
    """, (api_name, username))

    rows = cursor.fetchall()
    now = datetime.now()

    for row in rows:
        req_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")

        if (now - req_time).total_seconds() <= window:
            conn.close()
            return row[0]

    conn.close()
    return None