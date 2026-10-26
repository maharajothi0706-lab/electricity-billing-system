"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  REPORTING SERVICE MODULE
================================================================================
  Executes analytical SQL queries (aggregates, CTEs, GROUP BY, HAVING, Views)
  and produces CSV exports and tabular data for reports.
"""

import io
import csv
from database.db import execute_query

def get_monthly_consumption_report():
    """Retrieves monthly electricity consumption stats from the view."""
    return execute_query("SELECT * FROM monthly_consumption_summary ORDER BY reading_month DESC")

def get_revenue_summary_report():
    """Retrieves monthly billing and collection summary from the view."""
    return execute_query("SELECT * FROM v_revenue_by_month ORDER BY billing_period DESC")

def get_top_consumers_report(limit=10):
    """Retrieves top power consumers ranked by total consumption."""
    return execute_query(
        "SELECT * FROM v_top_consumers LIMIT %s",
        (limit,)
    )

def get_unpaid_bills_report(connection_type=None):
    """Retrieves all outstanding / unpaid bills with overdue calculations."""
    if connection_type and connection_type != 'ALL':
        return execute_query(
            "SELECT * FROM v_unpaid_bills WHERE connection_type = %s ORDER BY due_date ASC",
            (connection_type,)
        )
    return execute_query("SELECT * FROM v_unpaid_bills ORDER BY due_date ASC")

def get_consumer_history_report(consumer_id):
    """Retrieves full meter reading and billing history for an individual consumer."""
    readings = execute_query(
        """
        SELECT 
            mr.reading_id, mr.reading_month, mr.previous_reading, mr.current_reading,
            mr.units_consumed, mr.reading_date, mr.is_billed,
            b.bill_number, b.total_amount, b.amount_paid, b.outstanding_amount, b.payment_status
        FROM meter_readings mr
        LEFT JOIN bills b ON mr.reading_id = b.meter_reading_id
        WHERE mr.consumer_id = %s
        ORDER BY mr.reading_month DESC
        """,
        (consumer_id,)
    )
    return readings

def get_consumption_anomalies_report(billing_period='2026-10'):
    """
    Identifies consumers whose consumption in a given billing cycle is more
    than 30% higher than their historical average consumption.
    Demonstrates advanced SQL using CTEs and subqueries.
    """
    return execute_query(
        """
        WITH consumer_history AS (
            SELECT 
                consumer_id,
                AVG(units_consumed) AS past_avg_units,
                COUNT(reading_id) AS past_readings_count
            FROM meter_readings
            WHERE reading_month < %s
            GROUP BY consumer_id
            HAVING COUNT(reading_id) >= 1
        )
        SELECT 
            c.consumer_id,
            c.consumer_number,
            c.full_name,
            c.connection_type,
            c.phone_number,
            mr.units_consumed AS current_month_units,
            ROUND(ch.past_avg_units, 2) AS historical_average_units,
            ROUND((mr.units_consumed - ch.past_avg_units), 2) AS spike_difference,
            ROUND(((mr.units_consumed - ch.past_avg_units) / ch.past_avg_units * 100.0), 2) AS percentage_increase
        FROM meter_readings mr
        JOIN consumers c ON mr.consumer_id = c.consumer_id
        JOIN consumer_history ch ON mr.consumer_id = ch.consumer_id
        WHERE mr.reading_month = %s
          AND mr.units_consumed > (ch.past_avg_units * 1.30)
        ORDER BY percentage_increase DESC
        """,
        (billing_period, billing_period)
    )

def export_to_csv(data, fieldnames=None):
    """
    Takes a list of dictionaries and converts it into a CSV string.
    """
    if not data:
        return ""

    if not fieldnames:
        fieldnames = list(data[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        # Convert non-string types safely
        clean_row = {k: str(row.get(k, '')) for k in fieldnames}
        writer.writerow(clean_row)

    return output.getvalue()
