"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  CONSUMER MANAGEMENT BLUEPRINT (CRUD)
================================================================================
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required, admin_required
from database.db import execute_query, execute_query_one, execute_dml
from datetime import datetime

consumers_bp = Blueprint("consumers", __name__, url_prefix="/consumers")

@consumers_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    conn_type = request.args.get("conn_type", "").strip()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT c.*, 
               COALESCE(SUM(b.total_amount), 0.00) AS total_billed,
               COALESCE(SUM(b.outstanding_amount), 0.00) AS total_outstanding
        FROM consumers c
        LEFT JOIN bills b ON c.consumer_id = b.consumer_id
        WHERE 1=1
    """
    params = []

    if search:
        sql += " AND (c.full_name ILIKE %s OR c.consumer_number ILIKE %s OR c.meter_number ILIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if conn_type and conn_type != "ALL":
        sql += " AND c.connection_type = %s"
        params.append(conn_type)

    if status and status != "ALL":
        sql += " AND c.account_status = %s"
        params.append(status)

    sql += " GROUP BY c.consumer_id ORDER BY c.consumer_id DESC"

    try:
        consumers = execute_query(sql, tuple(params))
    except Exception as e:
        flash(f"Error fetching consumers: {str(e)}", "danger")
        consumers = []

    return render_template(
        "consumers/index.html",
        consumers=consumers,
        search=search,
        conn_type=conn_type,
        status=status
    )

@consumers_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        consumer_number = request.form.get("consumer_number", "").strip().upper()
        full_name = request.form.get("full_name", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "Chennai").strip()
        phone_number = request.form.get("phone_number", "").strip()
        email = request.form.get("email", "").strip()
        meter_number = request.form.get("meter_number", "").strip().upper()
        connection_type = request.form.get("connection_type", "DOMESTIC").strip()
        connection_date = request.form.get("connection_date", datetime.now().strftime("%Y-%m-%d"))

        # Validation
        if not consumer_number or not full_name or not meter_number or not phone_number:
            flash("Consumer number, full name, phone number, and meter number are mandatory.", "danger")
            return render_template("consumers/form.html", action="add", form=request.form)

        try:
            # Check duplicate consumer number
            exist_c = execute_query_one("SELECT 1 FROM consumers WHERE consumer_number = %s", (consumer_number,))
            if exist_c:
                flash(f"A consumer with reference '{consumer_number}' already exists.", "danger")
                return render_template("consumers/form.html", action="add", form=request.form)

            # Check duplicate meter number
            exist_m = execute_query_one("SELECT 1 FROM consumers WHERE meter_number = %s", (meter_number,))
            if exist_m:
                flash(f"A meter with hardware ID '{meter_number}' is already registered.", "danger")
                return render_template("consumers/form.html", action="add", form=request.form)

            execute_dml(
                """
                INSERT INTO consumers (
                    consumer_number, full_name, address, city, phone_number,
                    email, meter_number, connection_type, connection_date, account_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                """,
                (consumer_number, full_name, address, city, phone_number, email, meter_number, connection_type, connection_date)
            )
            flash(f"Consumer '{full_name}' ({consumer_number}) successfully registered!", "success")
            return redirect(url_for("consumers.index"))
        except Exception as e:
            flash(f"Database insertion failed: {str(e)}", "danger")

    # Auto-generate suggestion for next consumer number
    try:
        max_c = execute_query_one("SELECT COUNT(*) + 1001 AS next_num FROM consumers")
        suggested_num = f"CONS-{max_c['next_num']}" if max_c else "CONS-1019"
        suggested_meter = f"MTR-{suggested_num.split('-')[1]}"
    except Exception:
        suggested_num = "CONS-1019"
        suggested_meter = "MTR-5019"

    default_form = {
        "consumer_number": suggested_num,
        "meter_number": suggested_meter,
        "city": "Chennai",
        "connection_type": "DOMESTIC",
        "connection_date": datetime.now().strftime("%Y-%m-%d")
    }
    return render_template("consumers/form.html", action="add", form=default_form)

@consumers_bp.route("/<int:consumer_id>")
@login_required
def view(consumer_id):
    consumer = execute_query_one("SELECT * FROM consumers WHERE consumer_id = %s", (consumer_id,))
    if not consumer:
        flash("Consumer not found.", "danger")
        return redirect(url_for("consumers.index"))

    readings = execute_query(
        """
        SELECT mr.*, b.bill_id, b.bill_number, b.total_amount, b.amount_paid,
               b.outstanding_amount, b.payment_status
        FROM meter_readings mr
        LEFT JOIN bills b ON mr.reading_id = b.meter_reading_id
        WHERE mr.consumer_id = %s
        ORDER BY mr.reading_month DESC
        """,
        (consumer_id,)
    )

    bills = execute_query(
        "SELECT * FROM bills WHERE consumer_id = %s ORDER BY billing_period DESC",
        (consumer_id,)
    )

    summary = execute_query_one(
        "SELECT * FROM consumer_billing_summary WHERE consumer_id = %s",
        (consumer_id,)
    )

    return render_template(
        "consumers/view.html",
        consumer=consumer,
        readings=readings,
        bills=bills,
        summary=summary
    )

@consumers_bp.route("/<int:consumer_id>/edit", methods=["GET", "POST"])
@login_required
def edit(consumer_id):
    consumer = execute_query_one("SELECT * FROM consumers WHERE consumer_id = %s", (consumer_id,))
    if not consumer:
        flash("Consumer not found.", "danger")
        return redirect(url_for("consumers.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        email = request.form.get("email", "").strip()
        connection_type = request.form.get("connection_type", "").strip()
        account_status = request.form.get("account_status", "ACTIVE").strip()

        try:
            execute_dml(
                """
                UPDATE consumers
                SET full_name = %s, address = %s, city = %s, phone_number = %s,
                    email = %s, connection_type = %s, account_status = %s
                WHERE consumer_id = %s
                """,
                (full_name, address, city, phone_number, email, connection_type, account_status, consumer_id)
            )
            flash(f"Consumer '{consumer['consumer_number']}' updated successfully.", "success")
            return redirect(url_for("consumers.view", consumer_id=consumer_id))
        except Exception as e:
            flash(f"Update failed: {str(e)}", "danger")

    return render_template("consumers/form.html", action="edit", form=consumer)

@consumers_bp.route("/<int:consumer_id>/deactivate", methods=["POST"])
@admin_required
def deactivate(consumer_id):
    """Soft deactivates a consumer to preserve historical billing relations."""
    try:
        execute_dml(
            "UPDATE consumers SET account_status = 'INACTIVE' WHERE consumer_id = %s",
            (consumer_id,)
        )
        flash("Consumer connection deactivated successfully.", "info")
    except Exception as e:
        flash(f"Error deactivating consumer: {str(e)}", "danger")

    return redirect(url_for("consumers.view", consumer_id=consumer_id))

@consumers_bp.route("/<int:consumer_id>/activate", methods=["POST"])
@admin_required
def activate(consumer_id):
    """Reactivates an inactive consumer connection."""
    try:
        execute_dml(
            "UPDATE consumers SET account_status = 'ACTIVE' WHERE consumer_id = %s",
            (consumer_id,)
        )
        flash("Consumer connection reactivated.", "success")
    except Exception as e:
        flash(f"Error activating consumer: {str(e)}", "danger")

    return redirect(url_for("consumers.view", consumer_id=consumer_id))
