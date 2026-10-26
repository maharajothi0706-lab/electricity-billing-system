"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  PAYMENTS & AUDIT REVERSAL BLUEPRINT
================================================================================
"""

from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import login_required, admin_required
from database.db import execute_query, execute_query_one
from services.payment_service import record_bill_payment, reverse_payment

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")

@payments_bp.route("/")
@login_required
def index():
    method = request.args.get("method", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    sql = """
        SELECT p.*, b.bill_number, b.billing_period, b.total_amount AS bill_total,
               b.outstanding_amount AS bill_outstanding, b.payment_status AS bill_status,
               c.consumer_number, c.full_name
        FROM payments p
        JOIN bills b ON p.bill_id = b.bill_id
        JOIN consumers c ON b.consumer_id = c.consumer_id
        WHERE 1=1
    """
    params = []

    if method and method != "ALL":
        sql += " AND p.payment_method = %s"
        params.append(method)

    if status and status != "ALL":
        sql += " AND p.payment_status = %s"
        params.append(status)

    if search:
        sql += " AND (p.payment_reference ILIKE %s OR b.bill_number ILIKE %s OR c.consumer_number ILIKE %s OR c.full_name ILIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    sql += " ORDER BY p.payment_date DESC, p.payment_id DESC"

    try:
        payments = execute_query(sql, tuple(params))
        reversals = execute_query(
            """
            SELECT pr.*, p.payment_reference, b.bill_number, c.consumer_number, c.full_name
            FROM payment_reversals pr
            JOIN payments p ON pr.payment_id = p.payment_id
            JOIN bills b ON pr.bill_id = b.bill_id
            JOIN consumers c ON b.consumer_id = c.consumer_id
            ORDER BY pr.reversed_at DESC
            """
        )
    except Exception as e:
        flash(f"Error loading payments: {str(e)}", "danger")
        payments = []
        reversals = []

    return render_template(
        "payments/index.html",
        payments=payments,
        reversals=reversals,
        selected_method=method,
        selected_status=status,
        search=search
    )

@payments_bp.route("/record", methods=["GET", "POST"])
@login_required
def record():
    if request.method == "POST":
        bill_id = request.form.get("bill_id")
        amount = request.form.get("amount")
        payment_method = request.form.get("payment_method", "UPI")
        remarks = request.form.get("remarks", "").strip()

        if not bill_id or not amount:
            flash("Please specify a bill and payment amount.", "danger")
            return redirect(url_for("payments.record"))

        try:
            current_user = session.get("username", "system")
            res = record_bill_payment(
                bill_id=int(bill_id),
                amount=amount,
                payment_method=payment_method,
                remarks=remarks,
                recorded_by=current_user
            )
            flash(
                f"Payment of ₹{res['amount_paid']:.2f} recorded successfully! (Receipt: {res['payment_reference']}). Bill status is now {res['new_status']}.",
                "success"
            )
            return redirect(url_for("bills.view", bill_id=bill_id))
        except Exception as e:
            flash(f"Payment failed: {str(e)}", "danger")

    # Fetch all unpaid/partially paid bills for the dropdown
    preselected_bill_id = request.args.get("bill_id", "")
    unpaid_bills = execute_query(
        """
        SELECT b.bill_id, b.bill_number, b.billing_period, b.total_amount,
               b.amount_paid, b.outstanding_amount, b.due_date,
               c.consumer_number, c.full_name
        FROM bills b
        JOIN consumers c ON b.consumer_id = c.consumer_id
        WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
        ORDER BY b.due_date ASC
        """
    )

    selected_bill = None
    if preselected_bill_id:
        selected_bill = execute_query_one(
            """
            SELECT b.*, c.consumer_number, c.full_name
            FROM bills b
            JOIN consumers c ON b.consumer_id = c.consumer_id
            WHERE b.bill_id = %s
            """,
            (preselected_bill_id,)
        )

    return render_template(
        "payments/record.html",
        unpaid_bills=unpaid_bills,
        selected_bill=selected_bill,
        preselected_bill_id=preselected_bill_id
    )

@payments_bp.route("/<int:payment_id>/reverse", methods=["POST"])
@admin_required
def reverse(payment_id):
    """Audited reversal of an erroneous payment entry."""
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("A justification reason is required to cancel or reverse a payment.", "danger")
        return redirect(url_for("payments.index"))

    try:
        current_admin = session.get("username", "admin")
        res = reverse_payment(payment_id, reason, reversed_by=current_admin)
        flash(
            f"Payment #{payment_id} reversed successfully (₹{res['reversed_amount']:.2f}). Audit record #{res['reversal_id']} created. Bill status updated to {res['new_bill_status']}.",
            "warning"
        )
    except Exception as e:
        flash(f"Reversal failed: {str(e)}", "danger")

    return redirect(url_for("payments.index"))
