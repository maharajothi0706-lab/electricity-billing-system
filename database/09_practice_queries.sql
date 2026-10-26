/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 09: SQL LEARNING & VIVA PRACTICE QUERIES
================================================================================
  Purpose:
    Demonstrates working examples of all mandatory DBMS syllabus concepts:
    1. DDL (Data Definition Language): CREATE, ALTER, DROP (safe sandbox).
    2. DML (Data Manipulation Language): INSERT, UPDATE, DELETE.
    3. DQL (Data Query Language): SELECT, WHERE, ORDER BY, LIMIT.
    4. Relational Constraints: PK, FK, NOT NULL, UNIQUE, CHECK, DEFAULT.
    5. Table Joins: INNER JOIN, LEFT OUTER JOIN, Multi-Table JOIN.
    6. Aggregate Functions: SUM, AVG, COUNT, MIN, MAX.
    7. GROUP BY and HAVING Clauses.
    8. Subqueries: Scalar Subquery, Correlated Subquery, IN, EXISTS.
    9. Database Views.
    10. Performance Tuning with Indexes & EXPLAIN.
    11. ACID Transactions: BEGIN, SAVEPOINT, ROLLBACK, COMMIT.
    12. PostgreSQL Functions (PL/pgSQL).
    13. Stored Procedures (CREATE PROCEDURE, CALL).
    14. Database Triggers (BEFORE & AFTER).
    15. Database Normalization (1NF through 3NF Analysis).
    16. Consumption Anomaly Detection Query.
================================================================================
*/

-- =============================================================================
-- CONCEPT 1: DDL (DATA DEFINITION LANGUAGE)
-- Safe demonstration using a temporary practice table
-- =============================================================================
-- 1.1 CREATE TABLE demonstration
CREATE TABLE IF NOT EXISTS practice_audit_log (
    log_id SERIAL PRIMARY KEY,
    event_name VARCHAR(50) NOT NULL,
    logged_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 1.2 ALTER TABLE: Add a new column with a DEFAULT value
ALTER TABLE practice_audit_log 
    ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT 'Standard observation';

-- 1.3 ALTER TABLE: Add a CHECK constraint
ALTER TABLE practice_audit_log 
    ADD CONSTRAINT chk_event_name_length CHECK (LENGTH(event_name) >= 3);

-- 1.4 DROP TABLE safely
DROP TABLE IF EXISTS practice_audit_log;


-- =============================================================================
-- CONCEPT 2: DML (DATA MANIPULATION LANGUAGE)
-- =============================================================================
-- 2.1 INSERT: Adding a temporary consumer record for testing
INSERT INTO consumers (
    consumer_number, full_name, address, city, phone_number, email, 
    meter_number, connection_type, connection_date, account_status
) VALUES (
    'CONS-9999', 'Practice Test Consumer', '100, Test Street', 'Chennai', 
    '9999999999', 'test.user@example.com', 'MTR-TEST-9999', 'DOMESTIC', CURRENT_DATE, 'ACTIVE'
) ON CONFLICT (consumer_number) DO NOTHING;

-- 2.2 UPDATE: Updating contact information using parameterized filter
UPDATE consumers
SET phone_number = '9888888888',
    email = 'updated.test@example.com'
WHERE consumer_number = 'CONS-9999';

-- 2.3 DELETE: Removing test consumer safely
DELETE FROM consumers
WHERE consumer_number = 'CONS-9999';


-- =============================================================================
-- CONCEPT 3: DQL & BASIC FILTERING
-- =============================================================================
-- Retrieve all active commercial consumers sorted by name
SELECT 
    consumer_id, 
    consumer_number, 
    full_name, 
    city, 
    phone_number, 
    meter_number 
FROM consumers 
WHERE connection_type = 'COMMERCIAL' 
  AND account_status = 'ACTIVE'
ORDER BY full_name ASC;


-- =============================================================================
-- CONCEPT 4: INNER JOIN, LEFT JOIN & MULTI-TABLE JOIN
-- =============================================================================
-- 4.1 INNER JOIN: Get meter readings matched with their consumer details
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    mr.reading_month,
    mr.previous_reading,
    mr.current_reading,
    mr.units_consumed
FROM meter_readings mr
INNER JOIN consumers c ON mr.consumer_id = c.consumer_id
WHERE mr.reading_month = '2026-09'
ORDER BY mr.units_consumed DESC;

-- 4.2 LEFT OUTER JOIN: Show all consumers and their bills (including consumers who have never received a bill)
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    b.bill_number,
    b.billing_period,
    b.total_amount,
    b.payment_status
FROM consumers c
LEFT JOIN bills b ON c.consumer_id = b.consumer_id
ORDER BY c.consumer_id ASC, b.billing_period DESC;

-- 4.3 Multi-Table JOIN: Link Consumers -> Bills -> Payments
SELECT 
    c.consumer_number,
    c.full_name,
    b.bill_number,
    b.total_amount AS invoice_total,
    p.payment_reference,
    p.amount_paid,
    p.payment_method,
    p.payment_date
FROM consumers c
INNER JOIN bills b ON c.consumer_id = b.consumer_id
INNER JOIN payments p ON b.bill_id = p.bill_id
WHERE p.payment_status = 'SUCCESS'
ORDER BY p.payment_date DESC;


-- =============================================================================
-- CONCEPT 5: AGGREGATE FUNCTIONS (SUM, AVG, COUNT, MIN, MAX)
-- =============================================================================
SELECT 
    COUNT(bill_id) AS total_bills_issued,
    SUM(total_amount) AS total_revenue_invoiced,
    SUM(amount_paid) AS total_collected_revenue,
    SUM(outstanding_amount) AS total_outstanding_dues,
    ROUND(AVG(total_amount), 2) AS average_bill_amount,
    MIN(total_amount) AS smallest_bill,
    MAX(total_amount) AS largest_bill
FROM bills;


-- =============================================================================
-- CONCEPT 6: GROUP BY AND HAVING
-- =============================================================================
-- Find connection types where average monthly consumption exceeds 200 units
SELECT 
    c.connection_type,
    COUNT(DISTINCT c.consumer_id) AS total_consumers,
    SUM(mr.units_consumed) AS total_units_consumed,
    ROUND(AVG(mr.units_consumed), 2) AS avg_units_per_reading
FROM consumers c
JOIN meter_readings mr ON c.consumer_id = mr.consumer_id
GROUP BY c.connection_type
HAVING AVG(mr.units_consumed) > 150.00
ORDER BY avg_units_per_reading DESC;


-- =============================================================================
-- CONCEPT 7: SUBQUERIES
-- =============================================================================
-- 7.1 Scalar Subquery: Find all bills with total amount higher than the system overall average
SELECT 
    bill_number, 
    consumer_id, 
    units_consumed, 
    total_amount 
FROM bills
WHERE total_amount > (SELECT AVG(total_amount) FROM bills)
ORDER BY total_amount DESC;

-- 7.2 Subquery with IN: Find consumers who currently have unpaid or partially paid bills
SELECT 
    consumer_id, 
    consumer_number, 
    full_name, 
    phone_number 
FROM consumers 
WHERE consumer_id IN (
    SELECT DISTINCT consumer_id 
    FROM bills 
    WHERE payment_status IN ('UNPAID', 'PARTIALLY PAID')
);

-- 7.3 Correlated Subquery with EXISTS: Consumers who have at least one payment recorded via UPI
SELECT 
    c.consumer_number, 
    c.full_name 
FROM consumers c
WHERE EXISTS (
    SELECT 1 
    FROM bills b 
    JOIN payments p ON b.bill_id = p.bill_id
    WHERE b.consumer_id = c.consumer_id 
      AND p.payment_method = 'UPI'
);


-- =============================================================================
-- CONCEPT 8: QUERYING VIEWS
-- =============================================================================
-- View: consumer_billing_summary (demonstrates pre-aggregated metrics without duplicate joins)
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
ORDER BY total_outstanding_amount DESC;


-- =============================================================================
-- CONCEPT 9: INDEX PERFORMANCE ANALYSIS (EXPLAIN ANALYZE)
-- =============================================================================
-- In pgAdmin or psql, EXPLAIN ANALYZE shows the query execution plan and whether
-- an Index Scan or Sequential Scan was performed by PostgreSQL's query optimizer:
EXPLAIN ANALYZE
SELECT * FROM consumers WHERE consumer_number = 'CONS-1001';


-- =============================================================================
-- CONCEPT 10: ACID TRANSACTIONS (BEGIN, COMMIT, ROLLBACK)
-- =============================================================================
/*
  Demonstration of an ACID Transaction:
  If any step fails, ROLLBACK restores the database to its pristine state.
*/
BEGIN;
    -- Step 1: Update reading remarks
    UPDATE meter_readings 
    SET reading_remarks = 'Inspected during routine safety audit'
    WHERE reading_id = 1;

    -- Step 2: Test Savepoint
    SAVEPOINT audit_savepoint;

    -- Step 3: Intentional rollback to savepoint (demonstrating partial undo)
    ROLLBACK TO SAVEPOINT audit_savepoint;

-- Finalize transaction
COMMIT;


-- =============================================================================
-- CONCEPT 11: CONSUMPTION ANOMALY DETECTION REPORT
-- Consumers whose current month consumption is > 30% higher than their past average
-- =============================================================================
WITH consumer_history AS (
    SELECT 
        consumer_id,
        AVG(units_consumed) AS past_avg_units
    FROM meter_readings
    WHERE reading_month < '2026-10'
    GROUP BY consumer_id
)
SELECT 
    c.consumer_number,
    c.full_name,
    c.connection_type,
    mr.units_consumed AS oct_2026_units,
    ROUND(ch.past_avg_units, 2) AS past_avg_units,
    ROUND(((mr.units_consumed - ch.past_avg_units) / ch.past_avg_units * 100.0), 2) AS percentage_increase
FROM meter_readings mr
JOIN consumers c ON mr.consumer_id = c.consumer_id
JOIN consumer_history ch ON mr.consumer_id = ch.consumer_id
WHERE mr.reading_month = '2026-10'
  AND mr.units_consumed > (ch.past_avg_units * 1.30)
ORDER BY percentage_increase DESC;
