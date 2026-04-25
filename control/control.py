from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session

from Config import API_LIMITS, TIME_WINDOW, TIER_LIMITS
from database import (
    add_user, update_last_login, get_api_usage, log_api_call,
    get_earliest_request_time, connect, verify_user,
    get_user_tier, get_previous_window_usage
)
from api_res import get_api_specific_response

controllers = Blueprint("controllers", __name__, template_folder="../templates")


# 🔥 ANOMALY DETECTION
def detect_anomaly(current, previous):
    if previous == 0:
        return current >= 5
    return current > 2 * previous


# ---------------- LOGIN ----------------
@controllers.route("/", methods=["GET", "POST"])
@controllers.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if verify_user(username, password):
            session["username"] = username
            update_last_login(username)
            return redirect(url_for("controllers.plans"))
        else:
            error = "Invalid login"

    return render_template("login.html", error=error)


# ---------------- SIGNUP ----------------
@controllers.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        add_user(username, password)
        session["username"] = username

        return redirect(url_for("controllers.plans"))

    return render_template("sign_up.html")


# ---------------- PLANS ----------------
@controllers.route("/plans")
def plans():
    if not session.get("username"):
        return redirect(url_for("controllers.login"))
    return render_template("plans.html")


# ---------------- SELECT PLAN ----------------
@controllers.route("/select_plan/<plan>")
def select_plan(plan):
    username = session["username"]

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET tier=? WHERE username=?", (plan, username))
    conn.commit()
    conn.close()

    return redirect(url_for("controllers.dashboard"))


# ---------------- DASHBOARD ----------------
@controllers.route("/dashboard")
def dashboard():
    username = session["username"]

    tier = get_user_tier(username)
    multiplier = TIER_LIMITS.get(tier, 1)

    api_data = []

    for api_name, base_limit in API_LIMITS.items():
        limit = base_limit * multiplier
        used = get_api_usage(api_name, TIME_WINDOW, username)

        # 🔥 CLEAN RESET FIX
        if used >= limit:
            display_used = 0
        elif used == 0:
            display_used = 0
        else:
            display_used = used

        api_data.append({
            "name": api_name,
            "limit": limit,
            "used": display_used,
            "remaining": max(limit - display_used, 0)
        })

    return render_template(
        "dashboard.html",
        api_data=api_data,
        username=username,
        tier=tier
    )


# ---------------- API CALL ----------------
@controllers.route("/call/<api_name>")
def call_api(api_name):
    username = session["username"]

    tier = get_user_tier(username)
    multiplier = TIER_LIMITS.get(tier, 1)

    base_limit = API_LIMITS.get(api_name)
    dynamic_limit = base_limit * multiplier

    used = get_api_usage(api_name, TIME_WINDOW, username)
    previous = get_previous_window_usage(api_name, TIME_WINDOW, username)

    anomaly = detect_anomaly(used, previous)

    if used < dynamic_limit:
        log_api_call(api_name, username)

        return render_template(
            "result.html",
            api=api_name,
            status="Allowed",
            remaining=dynamic_limit - (used + 1),
            data=get_api_specific_response(api_name),
            username=username,
            tier=tier,
            anomaly=anomaly,
            used=used,
            limit=dynamic_limit,
            previous=previous
        )

    else:
        earliest = get_earliest_request_time(api_name, TIME_WINDOW, username)

        if earliest:
            earliest_time = datetime.strptime(earliest, "%Y-%m-%d %H:%M:%S")
            expire_time = earliest_time + timedelta(seconds=TIME_WINDOW)

            retry_after = int(max((expire_time - datetime.now()).total_seconds(), 0))
        else:
            retry_after = TIME_WINDOW

        return render_template(
            "result.html",
            api=api_name,
            status="Blocked",
            retry_after=retry_after,
            username=username,
            tier=tier,
            anomaly=True,
            used=used,
            limit=dynamic_limit,
            previous=previous
        )


# ---------------- LOGOUT ----------------
@controllers.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("controllers.login"))