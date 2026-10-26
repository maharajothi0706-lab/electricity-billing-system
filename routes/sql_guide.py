"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SQL CONCEPTS & ACADEMIC VIVA GUIDE BLUEPRINT
================================================================================
  Dedicated interactive module for college lab practicals and viva demonstration.
  Presents ER Diagram, Schema definitions, Normalization walkthrough,
  and live execution of syllabus SQL queries.
"""

from flask import Blueprint, render_template, request, jsonify
from routes.auth import login_required
from database.db import execute_query, test_connection

sql_guide_bp = Blueprint("sql_guide", __name__, url_prefix="/sql-guide")

DEMO_QUERIES = [
    {
        "id": "inner_join",
        "title": "1. INNER JOIN (Consumers with Meter Readings)",
        "concept": "INNER JOIN returns only rows with matching values in both tables.",
        "sql": """
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    mr.reading_month,
    mr.units_consumed
FROM meter_readings mr
INNER JOIN consumers c ON mr.consumer_id = c.consumer_id
WHERE mr.reading_month = '2026-09'
ORDER BY mr.units_consumed DESC
LIMIT 8;
        """
    },
    {
        "id": "left_join",
        "title": "2. LEFT OUTER JOIN (Consumers and Unbilled/Billed Status)",
        "concept": "LEFT JOIN preserves all rows from the left table even if no matching right record exists.",
        "sql": """
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    COALESCE(b.bill_number, 'NO BILL GENERATED') AS bill_number,
    COALESCE(b.total_amount, 0.00) AS total_amount,
    COALESCE(b.payment_status, 'N/A') AS payment_status
FROM consumers c
LEFT JOIN bills b ON c.consumer_id = b.consumer_id AND b.billing_period = '2026-10'
ORDER BY c.consumer_id ASC
LIMIT 8;
        """
    },
    {
        "id": "aggregates_group_by",
        "title": "3. Aggregates with GROUP BY & HAVING",
        "concept": "Groups records and filters aggregated results using the HAVING clause.",
        "sql": """
SELECT 
    c.connection_type,
    COUNT(DISTINCT c.consumer_id) AS total_consumers,
    SUM(mr.units_consumed) AS total_units_consumed,
    ROUND(AVG(mr.units_consumed), 2) AS avg_units_per_reading,
    MAX(mr.units_consumed) AS peak_consumption_units
FROM consumers c
JOIN meter_readings mr ON c.consumer_id = mr.consumer_id
GROUP BY c.connection_type
HAVING AVG(mr.units_consumed) > 100.00
ORDER BY avg_units_per_reading DESC;
        """
    },
    {
        "id": "scalar_subquery",
        "title": "4. Scalar Subquery (Bills Above System Average)",
        "concept": "A subquery that returns a single atomic value used in a WHERE comparison.",
        "sql": """
SELECT 
    bill_number, 
    billing_period, 
    units_consumed, 
    total_amount, 
    payment_status
FROM bills
WHERE total_amount > (SELECT AVG(total_amount) FROM bills)
ORDER BY total_amount DESC
LIMIT 6;
        """
    },
    {
        "id": "correlated_subquery",
        "title": "5. Correlated Subquery with EXISTS",
        "concept": "The inner query references columns from the outer query row-by-row.",
        "sql": """
SELECT 
    c.consumer_number, 
    c.full_name,
    c.connection_type,
    c.phone_number
FROM consumers c
WHERE EXISTS (
    SELECT 1 
    FROM bills b 
    JOIN payments p ON b.bill_id = p.bill_id
    WHERE b.consumer_id = c.consumer_id 
      AND p.payment_method = 'UPI'
)
LIMIT 6;
        """
    },
    {
        "id": "window_dense_rank",
        "title": "6. Window Function: DENSE_RANK()",
        "concept": "Ranks rows within a partition without collapsing the result set.",
        "sql": """
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    SUM(mr.units_consumed) AS total_lifetime_units,
    DENSE_RANK() OVER (ORDER BY SUM(mr.units_consumed) DESC) AS overall_consumption_rank
FROM consumers c
JOIN meter_readings mr ON c.consumer_id = mr.consumer_id
GROUP BY c.consumer_id, c.consumer_number, c.full_name, c.connection_type
ORDER BY overall_consumption_rank ASC
LIMIT 6;
        """
    },
    {
        "id": "view_query",
        "title": "7. Querying Reporting View (consumer_billing_summary)",
        "concept": "Demonstrates pre-aggregated SQL views preventing Cartesian join duplication.",
        "sql": """
SELECT 
    consumer_number,
    full_name,
    connection_type,
    total_units_consumed,
    total_billed_amount,
    total_paid_amount,
    total_outstanding_amount
FROM consumer_billing_summary
WHERE total_outstanding_amount > 0
ORDER BY total_outstanding_amount DESC
LIMIT 6;
        """
    }
]

@sql_guide_bp.route("/")
@login_required
def index():
    is_connected, _ = test_connection()
    return render_template(
        "sql_guide/index.html",
        demo_queries=DEMO_QUERIES,
        is_connected=is_connected
    )

@sql_guide_bp.route("/api/run-query", methods=["POST"])
@login_required
def run_query():
    """Allows safe execution of pre-approved practice demonstration queries."""
    query_id = request.json.get("query_id")
    target = next((q for q in DEMO_QUERIES if q["id"] == query_id), None)

    if not target:
        return jsonify({"error": "Unknown demo query ID."}), 400

    try:
        results = execute_query(target["sql"])
        # Format results for JSON response
        formatted_results = []
        for row in results:
            formatted_results.append({k: (str(v) if v is not None else "NULL") for k, v in row.items()})

        columns = list(results[0].keys()) if results else []
        return jsonify({
            "title": target["title"],
            "sql": target["sql"].strip(),
            "columns": columns,
            "rows": formatted_results,
            "row_count": len(formatted_results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
