from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

from Config import API_LIMITS, TIME_WINDOW, TIER_LIMITS
from database import (
    add_user, update_last_login, get_api_usage, log_api_call,
    get_earliest_request_time, connect, verify_user,
    get_user_tier, has_selected_plan
)
from api_res import get_api_specific_response

controllers = Blueprint("controllers", __name__, template_folder="templates")


# ---------------- LOGIN ----------------
@controllers.route("/", methods=["GET", "POST"])
@controllers.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("controllers.dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            if verify_user(username, password):
                update_last_login(username)
                session["username"] = username

                # 👉 Check plan
                if has_selected_plan(username):
                    return redirect(url_for("controllers.dashboard"))
                else:
                    return redirect(url_for("controllers.plans"))
            else:
                error = "Invalid login"
        else:
            error = "Enter username & password"

    return render_template("login.html", error=error)


# ---------------- SIGN UP ----------------
@controllers.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if session.get("username"):
        return redirect(url_for("controllers.dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            add_user(username, password)
            session["username"] = username
            update_last_login(username)

            return redirect(url_for("controllers.plans"))
        else:
            error = "Enter username & password"

    return render_template("sign_up.html", error=error)


# ---------------- PLAN PAGE ----------------
@controllers.route("/plans")
def plans():
    if not session.get("username"):
        return redirect(url_for("controllers.login"))

    username = session["username"]

    # Skip if already selected
    if has_selected_plan(username):
        return redirect(url_for("controllers.dashboard"))

    return render_template("plans.html")


# ---------------- SELECT PLAN ----------------
@controllers.route("/select_plan/<plan>")
def select_plan(plan):
    if not session.get("username"):
        return redirect(url_for("controllers.login"))

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
    if not session.get("username"):
        return redirect(url_for("controllers.login"))

    username = session["username"]
    tier = get_user_tier(username)
    multiplier = TIER_LIMITS.get(tier, 1)

    api_data = []

    for api_name, base_limit in API_LIMITS.items():
        limit = base_limit * multiplier
        used = get_api_usage(api_name, TIME_WINDOW, username)
        remaining = max(limit - used, 0)

        api_data.append({
            "name": api_name,
            "limit": limit,
            "used": used,
            "remaining": remaining
        })

    return render_template("dashboard.html", api_data=api_data, username=username, tier=tier)


# ---------------- API CALL ----------------
@controllers.route("/call/<api_name>")
def call_api(api_name):
    if not session.get("username"):
        return redirect(url_for("controllers.login"))

    username = session["username"]

    tier = get_user_tier(username)
    multiplier = TIER_LIMITS.get(tier, 1)

    base_limit = API_LIMITS.get(api_name)
    dynamic_limit = base_limit * multiplier

    used = get_api_usage(api_name, TIME_WINDOW, username)

    anomaly = used > (0.8 * dynamic_limit)

    if used < dynamic_limit:
        log_api_call(api_name, username)

        remaining = dynamic_limit - (used + 1)
        current_time = datetime.now()

        data = get_api_specific_response(
            api_name,
            username=username if api_name == "Get Profile" else None
        )

        return render_template(
            "result.html",
            api=api_name,
            status="Allowed",
            time=current_time.strftime("%I:%M:%S %p"),
            remaining=remaining,
            data=data,
            username=username,
            tier=tier,
            anomaly=anomaly
        )
    else:
        earliest = get_earliest_request_time(api_name, TIME_WINDOW, username)

        if earliest:
            earliest_time = datetime.strptime(earliest, "%Y-%m-%d %H:%M:%S")
            expire_time = earliest_time + timedelta(seconds=TIME_WINDOW)
            retry_after = int(max((expire_time - datetime.now()).total_seconds(), 0))
            retry_after = min(retry_after + 1, TIME_WINDOW)
        else:
            retry_after = TIME_WINDOW

        current_time = datetime.now()

        return render_template(
            "result.html",
            api=api_name,
            status="Blocked",
            time=current_time.strftime("%I:%M:%S %p"),
            retry_after=retry_after,
            data=None,
            username=username,
            tier=tier,
            anomaly=True
        )


# ---------------- LOGOUT ----------------
@controllers.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("controllers.login"))