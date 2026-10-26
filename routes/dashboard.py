"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  DASHBOARD BLUEPRINT
================================================================================
  Renders live operational statistics, KPI summary cards, and Chart.js graphs
  queried directly from PostgreSQL.
"""

from flask import Blueprint, render_template, jsonify
from routes.auth import login_required
from database.db import execute_query, execute_query_one, test_connection

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    # Test DB status
    is_connected, db_status_msg = test_connection()

    stats = {
        "total_consumers": 0,
        "units_this_month": 0,
        "total_bills": 0,
        "total_collected": 0.0,
        "total_outstanding": 0.0,
        "unpaid_bills_count": 0,
        "current_month": "2026-10"
    }
    recent_readings = []
    recent_bills = []
    unpaid_bills = []

    if is_connected:
        try:
            # 1. Total consumers
            res = execute_query_one("SELECT COUNT(*) AS count FROM consumers WHERE account_status = 'ACTIVE'")
            stats["total_consumers"] = res["count"] if res else 0

            # 2. Latest active month & units consumed
            month_row = execute_query_one("SELECT MAX(reading_month) AS max_m FROM meter_readings")
            latest_month = month_row["max_m"] if month_row and month_row["max_m"] else "2026-10"
            stats["current_month"] = latest_month

            res = execute_query_one(
                "SELECT COALESCE(SUM(units_consumed), 0.00) AS units FROM meter_readings WHERE reading_month = %s",
                (latest_month,)
            )
            stats["units_this_month"] = float(res["units"]) if res else 0.0

            # 3. Billing & payment aggregates
            res = execute_query_one(
                """
                SELECT 
                    COUNT(bill_id) AS total_bills,
                    COALESCE(SUM(amount_paid), 0.00) AS total_collected,
                    COALESCE(SUM(outstanding_amount), 0.00) AS total_outstanding,
                    COUNT(CASE WHEN payment_status IN ('UNPAID', 'PARTIALLY PAID') THEN 1 END) AS unpaid_count
                FROM bills
                """
            )
            if res:
                stats["total_bills"] = res["total_bills"]
                stats["total_collected"] = float(res["total_collected"])
                stats["total_outstanding"] = float(res["total_outstanding"])
                stats["unpaid_bills_count"] = res["unpaid_count"]

            # 4. Recent meter readings
            recent_readings = execute_query(
                """
                SELECT mr.reading_id, mr.reading_month, mr.previous_reading, mr.current_reading,
                       mr.units_consumed, mr.reading_date, mr.is_billed,
                       c.consumer_number, c.full_name, c.connection_type
                FROM meter_readings mr
                JOIN consumers c ON mr.consumer_id = c.consumer_id
                ORDER BY mr.reading_date DESC, mr.reading_id DESC
                LIMIT 5
                """
            )

            # 5. Recently generated bills
            recent_bills = execute_query(
                """
                SELECT b.bill_id, b.bill_number, b.billing_period, b.units_consumed,
                       b.total_amount, b.amount_paid, b.outstanding_amount, b.payment_status,
                       c.consumer_number, c.full_name
                FROM bills b
                JOIN consumers c ON b.consumer_id = c.consumer_id
                ORDER BY b.bill_date DESC, b.bill_id DESC
                LIMIT 5
                """
            )

            # 6. Unpaid bills requiring attention
            unpaid_bills = execute_query(
                """
                SELECT b.bill_id, b.bill_number, b.billing_period, b.total_amount,
                       b.amount_paid, b.outstanding_amount, b.due_date, b.payment_status,
                       c.consumer_id, c.consumer_number, c.full_name, c.phone_number
                FROM bills b
                JOIN consumers c ON b.consumer_id = c.consumer_id
                WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
                ORDER BY b.due_date ASC
                LIMIT 5
                """
            )

        except Exception as e:
            db_status_msg = f"Query error: {str(e)}"

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_readings=recent_readings,
        recent_bills=recent_bills,
        unpaid_bills=unpaid_bills,
        is_connected=is_connected,
        db_status_msg=db_status_msg
    )

@dashboard_bp.route("/api/dashboard-charts")
@login_required
def chart_data():
    """Returns dynamic Chart.js JSON datasets."""
    is_connected, _ = test_connection()
    if not is_connected:
        return jsonify({
            "consumption": {"labels": [], "data": []},
            "revenue": {"labels": [], "data": []},
            "status": {"labels": ["Paid", "Partially Paid", "Unpaid"], "data": [0, 0, 0]},
            "top_consumers": {"labels": [], "data": []}
        })

    # 1. Monthly consumption
    consumption_rows = execute_query(
        """
        SELECT reading_month, SUM(units_consumed) AS units
        FROM meter_readings
        GROUP BY reading_month
        ORDER BY reading_month ASC
        """
    )
    c_labels = [r["reading_month"] for r in consumption_rows]
    c_data = [float(r["units"]) for r in consumption_rows]

    # 2. Monthly revenue collected
    rev_rows = execute_query(
        """
        SELECT billing_period, SUM(amount_paid) AS collected, SUM(total_amount) AS billed
        FROM bills
        GROUP BY billing_period
        ORDER BY billing_period ASC
        """
    )
    r_labels = [r["billing_period"] for r in rev_rows]
    r_collected = [float(r["collected"]) for r in rev_rows]
    r_billed = [float(r["billed"]) for r in rev_rows]

    # 3. Bill payment statuses
    status_rows = execute_query(
        """
        SELECT payment_status, COUNT(*) AS count
        FROM bills
        GROUP BY payment_status
        """
    )
    status_map = {"PAID": 0, "PARTIALLY PAID": 0, "UNPAID": 0}
    for row in status_rows:
        status_map[row["payment_status"]] = row["count"]

    # 4. Top 5 consumers by total consumption
    top_rows = execute_query(
        """
        SELECT c.full_name, SUM(mr.units_consumed) AS total_units
        FROM meter_readings mr
        JOIN consumers c ON mr.consumer_id = c.consumer_id
        GROUP BY c.consumer_id, c.full_name
        ORDER BY total_units DESC
        LIMIT 5
        """
    )
    t_labels = [r["full_name"] for r in top_rows]
    t_data = [float(r["total_units"]) for r in top_rows]

    return jsonify({
        "consumption": {
            "labels": c_labels,
            "data": c_data
        },
        "revenue": {
            "labels": r_labels,
            "collected": r_collected,
            "billed": r_billed
        },
        "status": {
            "labels": ["Paid", "Partially Paid", "Unpaid"],
            "data": [status_map["PAID"], status_map["PARTIALLY PAID"], status_map["UNPAID"]]
        },
        "top_consumers": {
            "labels": t_labels,
            "data": t_data
        }
    })
