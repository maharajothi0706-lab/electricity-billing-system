"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  METER READING MANAGEMENT BLUEPRINT
================================================================================
"""

from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required
from database.db import execute_query, execute_query_one, execute_dml

readings_bp = Blueprint("readings", __name__, url_prefix="/readings")

@readings_bp.route("/")
@login_required
def index():
    period = request.args.get("period", "").strip()
    billed = request.args.get("billed", "").strip()
    search = request.args.get("search", "").strip()

    sql = """
        SELECT mr.*, c.consumer_number, c.full_name, c.connection_type, c.meter_number,
               b.bill_id, b.bill_number, b.total_amount, b.payment_status
        FROM meter_readings mr
        JOIN consumers c ON mr.consumer_id = c.consumer_id
        LEFT JOIN bills b ON mr.reading_id = b.meter_reading_id
        WHERE 1=1
    """
    params = []

    if period and period != "ALL":
        sql += " AND mr.reading_month = %s"
        params.append(period)

    if billed == "YES":
        sql += " AND mr.is_billed = TRUE"
    elif billed == "NO":
        sql += " AND mr.is_billed = FALSE"

    if search:
        sql += " AND (c.full_name ILIKE %s OR c.consumer_number ILIKE %s OR c.meter_number ILIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY mr.reading_month DESC, mr.reading_date DESC, mr.reading_id DESC"

    try:
        readings = execute_query(sql, tuple(params))
        # Unique periods for filter dropdown
        periods = execute_query("SELECT DISTINCT reading_month FROM meter_readings ORDER BY reading_month DESC")
    except Exception as e:
        flash(f"Error fetching meter readings: {str(e)}", "danger")
        readings = []
        periods = []

    return render_template(
        "readings/index.html",
        readings=readings,
        periods=[p["reading_month"] for p in periods],
        selected_period=period,
        billed=billed,
        search=search
    )

@readings_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        consumer_id = request.form.get("consumer_id", "").strip()
        reading_month = request.form.get("reading_month", "").strip()
        previous_reading = request.form.get("previous_reading", "").strip()
        current_reading = request.form.get("current_reading", "").strip()
        reading_date = request.form.get("reading_date", datetime.now().strftime("%Y-%m-%d"))
        reading_remarks = request.form.get("reading_remarks", "").strip()

        if not consumer_id or not reading_month or not previous_reading or not current_reading:
            flash("All reading fields are mandatory.", "danger")
            return redirect(url_for("readings.add"))

        try:
            prev_dec = Decimal(previous_reading)
            curr_dec = Decimal(current_reading)

            if prev_dec < 0 or curr_dec < 0:
                flash("Meter readings cannot be negative numbers.", "danger")
                return redirect(url_for("readings.add"))

            if curr_dec < prev_dec:
                flash(f"Current reading ({curr_dec}) cannot be less than previous reading ({prev_dec}).", "danger")
                return redirect(url_for("readings.add"))

            units_consumed = curr_dec - prev_dec

            # Check duplicate reading for same consumer & month
            existing = execute_query_one(
                "SELECT 1 FROM meter_readings WHERE consumer_id = %s AND reading_month = %s",
                (consumer_id, reading_month)
            )
            if existing:
                flash(f"A reading for {reading_month} is already recorded for this consumer.", "danger")
                return redirect(url_for("readings.add"))

            # Check consumer is active
            c = execute_query_one("SELECT account_status FROM consumers WHERE consumer_id = %s", (consumer_id,))
            if not c or c["account_status"] != "ACTIVE":
                flash("Cannot enter readings for an inactive or non-existent consumer.", "danger")
                return redirect(url_for("readings.add"))

            execute_dml(
                """
                INSERT INTO meter_readings (
                    consumer_id, reading_month, previous_reading, current_reading,
                    units_consumed, reading_date, reading_remarks, is_billed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
                """,
                (consumer_id, reading_month, prev_dec, curr_dec, units_consumed, reading_date, reading_remarks)
            )

            flash(f"Meter reading recorded successfully ({units_consumed} units consumed)!", "success")
            return redirect(url_for("readings.index"))

        except Exception as e:
            flash(f"Failed to record meter reading: {str(e)}", "danger")

    consumers = execute_query(
        "SELECT consumer_id, consumer_number, full_name, meter_number, connection_type FROM consumers WHERE account_status = 'ACTIVE' ORDER BY full_name ASC"
    )
    preselected_consumer = request.args.get("consumer_id", "")
    current_month_str = datetime.now().strftime("%Y-%m")

    return render_template(
        "readings/form.html",
        consumers=consumers,
        preselected_consumer=preselected_consumer,
        current_month=current_month_str,
        today_date=datetime.now().strftime("%Y-%m-%d")
    )

@readings_bp.route("/api/consumer-latest-reading/<int:consumer_id>")
@login_required
def get_latest_reading(consumer_id):
    """API endpoint to auto-fill the previous reading when a consumer is chosen."""
    row = execute_query_one(
        """
        SELECT current_reading, reading_month 
        FROM meter_readings 
        WHERE consumer_id = %s 
        ORDER BY reading_month DESC, reading_date DESC 
        LIMIT 1
        """,
        (consumer_id,)
    )
    if row:
        return jsonify({
            "previous_reading": float(row["current_reading"]),
            "last_month": row["reading_month"]
        })
    return jsonify({
        "previous_reading": 0.0,
        "last_month": None
    })
