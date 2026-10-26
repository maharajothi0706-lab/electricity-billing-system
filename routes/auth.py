"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  AUTHENTICATION & AUTHORIZATION BLUEPRINT
================================================================================
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.db import execute_query_one

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "ADMIN":
            flash("Administrator privileges are required for this operation.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        try:
            user = execute_query_one(
                "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
                (username,)
            )

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["full_name"] = user["full_name"]
                session["role"] = user["role"]
                flash(f"Welcome back, {user['full_name']} ({user['role']})!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard.index"))
            else:
                flash("Invalid username or password.", "danger")
        except Exception as e:
            flash(f"Database error during login: {str(e)}", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
