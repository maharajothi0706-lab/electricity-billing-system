"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  BILL GENERATION & INVOICING BLUEPRINT
================================================================================
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from database.db import execute_query, execute_query_one
from services.billing_service import generate_bill_for_reading, batch_generate_bills_for_period

bills_bp = Blueprint("bills", __name__, url_prefix="/bills")

@bills_bp.route("/")
@login_required
def index():
    period = request.args.get("period", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    sql = """
        SELECT b.*, c.consumer_number, c.full_name, c.connection_type, c.meter_number
        FROM bills b
        JOIN consumers c ON b.consumer_id = c.consumer_id
        WHERE 1=1
    """
    params = []

    if period and period != "ALL":
        sql += " AND b.billing_period = %s"
        params.append(period)

    if status and status != "ALL":
        sql += " AND b.payment_status = %s"
        params.append(status)

    if search:
        sql += " AND (b.bill_number ILIKE %s OR c.consumer_number ILIKE %s OR c.full_name ILIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY b.bill_date DESC, b.bill_id DESC"

    try:
        bills = execute_query(sql, tuple(params))
        periods = execute_query("SELECT DISTINCT billing_period FROM bills ORDER BY billing_period DESC")
    except Exception as e:
        flash(f"Error loading bills: {str(e)}", "danger")
        bills = []
        periods = []

    return render_template(
        "bills/index.html",
        bills=bills,
        periods=[p["billing_period"] for p in periods],
        selected_period=period,
        selected_status=status,
        search=search
    )

@bills_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "POST":
        action_type = request.form.get("action_type", "single")

        if action_type == "single":
            reading_id = request.form.get("reading_id")
            if not reading_id:
                flash("Please choose an unbilled meter reading.", "warning")
                return redirect(url_for("bills.generate"))

            try:
                bill_id = generate_bill_for_reading(int(reading_id))
                flash("Bill generated successfully with progressive slab charges!", "success")
                return redirect(url_for("bills.view", bill_id=bill_id))
            except Exception as e:
                flash(f"Bill generation failed: {str(e)}", "danger")

        elif action_type == "batch":
            period = request.form.get("batch_period")
            if not period:
                flash("Please select a billing cycle month for batch generation.", "warning")
                return redirect(url_for("bills.generate"))

            gen_count, fail_count, errors = batch_generate_bills_for_period(period)
            if gen_count > 0:
                flash(f"Batch completed: {gen_count} bills generated successfully for period {period}!", "success")
            if fail_count > 0:
                flash(f"{fail_count} readings could not be billed: {'; '.join(errors[:3])}", "warning")

            return redirect(url_for("bills.index", period=period))

    # Fetch all unbilled readings
    unbilled_readings = execute_query(
        """
        SELECT mr.*, c.consumer_number, c.full_name, c.connection_type, c.meter_number
        FROM meter_readings mr
        JOIN consumers c ON mr.consumer_id = c.consumer_id
        WHERE mr.is_billed = FALSE
        ORDER BY mr.reading_month DESC, c.full_name ASC
        """
    )

    # Distinct periods of unbilled readings for batch generation dropdown
    unbilled_periods = execute_query(
        "SELECT DISTINCT reading_month FROM meter_readings WHERE is_billed = FALSE ORDER BY reading_month DESC"
    )

    return render_template(
        "bills/generate.html",
        unbilled_readings=unbilled_readings,
        unbilled_periods=[p["reading_month"] for p in unbilled_periods]
    )

@bills_bp.route("/<int:bill_id>")
@login_required
def view(bill_id):
    bill = execute_query_one(
        """
        SELECT b.*, c.consumer_number, c.full_name, c.address, c.city,
               c.phone_number, c.email, c.meter_number, c.connection_type,
               mr.previous_reading, mr.current_reading, mr.reading_date
        FROM bills b
        JOIN consumers c ON b.consumer_id = c.consumer_id
        JOIN meter_readings mr ON b.meter_reading_id = mr.reading_id
        WHERE b.bill_id = %s
        """,
        (bill_id,)
    )

    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("bills.index"))

    items = execute_query(
        "SELECT * FROM bill_items WHERE bill_id = %s ORDER BY item_id ASC",
        (bill_id,)
    )

    payments = execute_query(
        "SELECT * FROM payments WHERE bill_id = %s ORDER BY payment_date DESC",
        (bill_id,)
    )

    return render_template(
        "bills/view.html",
        bill=bill,
        items=items,
        payments=payments
    )

@bills_bp.route("/<int:bill_id>/print")
@login_required
def print_bill(bill_id):
    bill = execute_query_one(
        """
        SELECT b.*, c.consumer_number, c.full_name, c.address, c.city,
               c.phone_number, c.email, c.meter_number, c.connection_type,
               mr.previous_reading, mr.current_reading, mr.reading_date
        FROM bills b
        JOIN consumers c ON b.consumer_id = c.consumer_id
        JOIN meter_readings mr ON b.meter_reading_id = mr.reading_id
        WHERE b.bill_id = %s
        """,
        (bill_id,)
    )

    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("bills.index"))

    items = execute_query(
        "SELECT * FROM bill_items WHERE bill_id = %s ORDER BY item_id ASC",
        (bill_id,)
    )

    payments = execute_query(
        "SELECT * FROM payments WHERE bill_id = %s AND payment_status = 'SUCCESS' ORDER BY payment_date DESC",
        (bill_id,)
    )

    return render_template(
        "bills/print.html",
        bill=bill,
        items=items,
        payments=payments
    )
