"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  REPORTS & CSV EXPORT BLUEPRINT
================================================================================
"""

from flask import Blueprint, render_template, request, Response, flash
from routes.auth import login_required
from database.db import execute_query
from services.report_service import (
    get_monthly_consumption_report,
    get_revenue_summary_report,
    get_top_consumers_report,
    get_unpaid_bills_report,
    get_consumption_anomalies_report,
    export_to_csv
)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

@reports_bp.route("/")
@login_required
def index():
    report_type = request.args.get("type", "monthly_consumption")
    period = request.args.get("period", "2026-10")
    conn_type = request.args.get("conn_type", "ALL")

    data = []
    periods = []

    try:
        if report_type == "monthly_consumption":
            data = get_monthly_consumption_report()
        elif report_type == "revenue_summary":
            data = get_revenue_summary_report()
        elif report_type == "top_consumers":
            data = get_top_consumers_report(limit=15)
        elif report_type == "unpaid_bills":
            data = get_unpaid_bills_report(connection_type=conn_type)
        elif report_type == "anomalies":
            data = get_consumption_anomalies_report(billing_period=period)

        periods = execute_query("SELECT DISTINCT reading_month FROM meter_readings ORDER BY reading_month DESC")
    except Exception as e:
        flash(f"Error generating report '{report_type}': {str(e)}", "danger")

    return render_template(
        "reports/index.html",
        report_type=report_type,
        data=data,
        periods=[p["reading_month"] for p in periods],
        selected_period=period,
        selected_conn_type=conn_type
    )

@reports_bp.route("/export-csv")
@login_required
def export():
    report_type = request.args.get("type", "monthly_consumption")
    period = request.args.get("period", "2026-10")
    conn_type = request.args.get("conn_type", "ALL")

    data = []
    filename = f"{report_type}_report.csv"

    try:
        if report_type == "monthly_consumption":
            data = get_monthly_consumption_report()
        elif report_type == "revenue_summary":
            data = get_revenue_summary_report()
        elif report_type == "top_consumers":
            data = get_top_consumers_report(limit=50)
        elif report_type == "unpaid_bills":
            data = get_unpaid_bills_report(connection_type=conn_type)
        elif report_type == "anomalies":
            data = get_consumption_anomalies_report(billing_period=period)
            filename = f"consumption_anomalies_{period}.csv"

        csv_content = export_to_csv(data)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        flash(f"Export failed: {str(e)}", "danger")
        return render_template("reports/index.html", report_type=report_type, data=[])
