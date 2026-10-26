/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 07: DATABASE VIEWS
================================================================================
  Purpose:
    Provides pre-computed, secured, and normalized database views for reporting
    and dashboard queries without repeating complex JOIN logic in application code.

  Academic / Viva Note:
    - A View is a virtual table defined by a SQL query. It does not store physical
      data itself; instead, it executes its defining query dynamically.
    - JOIN Multiplication Danger (Fan-out problem):
      A common student pitfall occurs when joining tables with one-to-many
      relationships simultaneously (e.g. Consumer -> Bills -> Payments).
      If a bill has 3 payments, joining all three tables naively duplicates the
      bill amount 3 times, artificially tripling total billed revenue!
    - We solve this cleanly using Common Table Expressions (CTEs) or correlated
      subqueries to pre-aggregate payments before joining to bills and consumers.
================================================================================
*/

-- =============================================================================
-- VIEW 1: consumer_billing_summary
-- =============================================================================
/*
  Requirement 14.F:
  Shows consumer profile, lifetime consumption, billed amounts, payments,
  and outstanding balance without multiplying totals through incorrect joins.
*/
CREATE OR REPLACE VIEW consumer_billing_summary AS
WITH consumer_bills_agg AS (
    -- Pre-aggregate billing figures at the consumer level
    SELECT 
        b.consumer_id,
        COUNT(b.bill_id) AS total_bills_count,
        COALESCE(SUM(b.units_consumed), 0.00) AS total_units_consumed,
        COALESCE(SUM(b.total_amount), 0.00) AS total_billed_amount,
        COALESCE(SUM(b.amount_paid), 0.00) AS total_paid_amount,
        COALESCE(SUM(b.outstanding_amount), 0.00) AS total_outstanding_amount
    FROM bills b
    GROUP BY b.consumer_id
),
consumer_unpaid_agg AS (
    -- Pre-aggregate count of currently pending unpaid bills
    SELECT 
        b.consumer_id,
        COUNT(b.bill_id) AS unpaid_bills_count
    FROM bills b
    WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
    GROUP BY b.consumer_id
)
SELECT 
    c.consumer_id,
    c.consumer_number,
    c.full_name,
    c.phone_number,
    c.email,
    c.city,
    c.connection_type,
    c.meter_number,
    c.account_status,
    c.connection_date,
    COALESCE(ba.total_bills_count, 0) AS total_bills_count,
    COALESCE(ba.total_units_consumed, 0.00) AS total_units_consumed,
    COALESCE(ba.total_billed_amount, 0.00) AS total_billed_amount,
    COALESCE(ba.total_paid_amount, 0.00) AS total_paid_amount,
    COALESCE(ba.total_outstanding_amount, 0.00) AS total_outstanding_amount,
    COALESCE(ua.unpaid_bills_count, 0) AS unpaid_bills_count
FROM consumers c
LEFT JOIN consumer_bills_agg ba ON c.consumer_id = ba.consumer_id
LEFT JOIN consumer_unpaid_agg ua ON c.consumer_id = ua.consumer_id;

COMMENT ON VIEW consumer_billing_summary IS 
'Comprehensive summary of each consumer with consumption, billed, paid, and outstanding balances without Cartesian duplication.';


-- =============================================================================
-- VIEW 2: monthly_consumption_summary
-- =============================================================================
/*
  Requirement 14.G:
  Aggregates electricity consumption patterns grouped by billing month.
*/
CREATE OR REPLACE VIEW monthly_consumption_summary AS
SELECT 
    mr.reading_month,
    COUNT(DISTINCT mr.consumer_id) AS active_consumers_read,
    SUM(mr.units_consumed) AS total_units_consumed,
    ROUND(AVG(mr.units_consumed), 2) AS average_units_consumed,
    MIN(mr.units_consumed) AS minimum_units_consumed,
    MAX(mr.units_consumed) AS maximum_units_consumed
FROM meter_readings mr
GROUP BY mr.reading_month
ORDER BY mr.reading_month DESC;

COMMENT ON VIEW monthly_consumption_summary IS 
'Monthly aggregated consumption statistics including total, average, min, and max kilowatt-hours.';


-- =============================================================================
-- VIEW 3: v_revenue_by_month
-- =============================================================================
/*
  Shows monthly financial performance:
  Total Billed vs Total Collected vs Collection Efficiency Percentage.
*/
CREATE OR REPLACE VIEW v_revenue_by_month AS
SELECT 
    b.billing_period,
    COUNT(b.bill_id) AS total_bills_issued,
    SUM(b.units_consumed) AS total_units_billed,
    SUM(b.energy_charge) AS total_energy_charge,
    SUM(b.fixed_charge) AS total_fixed_charge,
    SUM(b.total_amount) AS total_billed_amount,
    SUM(b.amount_paid) AS total_collected_amount,
    SUM(b.outstanding_amount) AS total_outstanding_amount,
    CASE 
        WHEN SUM(b.total_amount) > 0 
        THEN ROUND((SUM(b.amount_paid) / SUM(b.total_amount) * 100.0), 2)
        ELSE 0.00 
    END AS collection_efficiency_percentage
FROM bills b
GROUP BY b.billing_period
ORDER BY b.billing_period DESC;

COMMENT ON VIEW v_revenue_by_month IS 
'Monthly billing and revenue collection performance metrics and collection efficiency.';


-- =============================================================================
-- VIEW 4: v_top_consumers
-- =============================================================================
/*
  Identifies top consumers by total consumption using SQL Window Function DENSE_RANK().
*/
CREATE OR REPLACE VIEW v_top_consumers AS
SELECT 
    c.consumer_id,
    c.consumer_number,
    c.full_name,
    c.connection_type,
    c.meter_number,
    SUM(mr.units_consumed) AS lifetime_units_consumed,
    ROUND(AVG(mr.units_consumed), 2) AS avg_monthly_units,
    DENSE_RANK() OVER (ORDER BY SUM(mr.units_consumed) DESC) AS consumption_rank
FROM consumers c
JOIN meter_readings mr ON c.consumer_id = mr.consumer_id
WHERE c.account_status = 'ACTIVE'
GROUP BY c.consumer_id, c.consumer_number, c.full_name, c.connection_type, c.meter_number
ORDER BY lifetime_units_consumed DESC;

COMMENT ON VIEW v_top_consumers IS 
'Ranking of consumers by total electrical energy usage using the DENSE_RANK() window function.';


-- =============================================================================
-- VIEW 5: v_unpaid_bills
-- =============================================================================
/*
  Lists all pending invoices with consumer contact info and overdue calculation.
*/
CREATE OR REPLACE VIEW v_unpaid_bills AS
SELECT 
    b.bill_id,
    b.bill_number,
    b.billing_period,
    c.consumer_id,
    c.consumer_number,
    c.full_name,
    c.phone_number,
    c.connection_type,
    b.units_consumed,
    b.total_amount,
    b.amount_paid,
    b.outstanding_amount,
    b.bill_date,
    b.due_date,
    b.payment_status,
    CASE 
        WHEN CURRENT_DATE > b.due_date THEN TRUE 
        ELSE FALSE 
    END AS is_overdue,
    GREATEST(0, (CURRENT_DATE - b.due_date)) AS days_overdue
FROM bills b
JOIN consumers c ON b.consumer_id = c.consumer_id
WHERE b.payment_status IN ('UNPAID', 'PARTIALLY PAID')
ORDER BY b.due_date ASC;

COMMENT ON VIEW v_unpaid_bills IS 
'Actionable list of all unpaid or partially settled electricity bills with overdue status.';
