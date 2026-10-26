/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 03: CONSTRAINTS AND INDEXES DEFINITION
================================================================================
  Purpose:
    Defines database indexes to accelerate frequently queried columns,
    foreign key lookups, and aggregate operations, while documenting
    how indexing improves query performance via B-Tree data structures.

  Academic / Viva Note:
    - Primary keys automatically create a unique B-Tree index in PostgreSQL.
    - Foreign keys do NOT automatically create indexes in PostgreSQL. Adding
      explicit indexes on foreign keys prevents slow sequential table scans
      during JOINs and cascade operations.
    - Composite indexes (e.g. consumer_id, reading_month) dramatically speed up
      multi-column search filters.
================================================================================
*/

-- =============================================================================
-- INDEXES ON CONSUMERS TABLE
-- =============================================================================
-- Accelerates lookups by alphanumeric consumer number in search bars
CREATE INDEX IF NOT EXISTS idx_consumers_consumer_number 
    ON consumers (consumer_number);

-- Accelerates lookups by physical meter identifier
CREATE INDEX IF NOT EXISTS idx_consumers_meter_number 
    ON consumers (meter_number);

-- Accelerates filtering by connection type (Domestic / Commercial / Industrial)
CREATE INDEX IF NOT EXISTS idx_consumers_connection_type 
    ON consumers (connection_type);

-- Accelerates filtering active vs inactive consumers on dashboard
CREATE INDEX IF NOT EXISTS idx_consumers_account_status 
    ON consumers (account_status);


-- =============================================================================
-- INDEXES ON TARIFF AND SLABS
-- =============================================================================
-- Speeds up retrieval of active tariff plans
CREATE INDEX IF NOT EXISTS idx_tariffs_connection_active 
    ON tariffs (connection_type, is_active);

-- Speeds up retrieval of progressive slabs belonging to a tariff
CREATE INDEX IF NOT EXISTS idx_tariff_slabs_tariff_id 
    ON tariff_slabs (tariff_id, slab_number);


-- =============================================================================
-- INDEXES ON METER READINGS
-- =============================================================================
-- Speeds up retrieval of a consumer's historical readings sorted by month
CREATE INDEX IF NOT EXISTS idx_meter_readings_consumer_month 
    ON meter_readings (consumer_id, reading_month);

-- Speeds up filtering for unbilled meter readings ready for invoice generation
CREATE INDEX IF NOT EXISTS idx_meter_readings_unbilled 
    ON meter_readings (is_billed) 
    WHERE is_billed = FALSE;


-- =============================================================================
-- INDEXES ON BILLS
-- =============================================================================
-- Accelerates consumer-wise bill lookup and history pages
CREATE INDEX IF NOT EXISTS idx_bills_consumer_id 
    ON bills (consumer_id);

-- Accelerates meter reading to bill 1-to-1 association checks
CREATE INDEX IF NOT EXISTS idx_bills_meter_reading_id 
    ON bills (meter_reading_id);

-- Speeds up monthly revenue aggregations and billing cycle reports
CREATE INDEX IF NOT EXISTS idx_bills_billing_period 
    ON bills (billing_period);

-- Speeds up dashboard queries for UNPAID and PARTIALLY PAID bills
CREATE INDEX IF NOT EXISTS idx_bills_payment_status 
    ON bills (payment_status);

-- Speeds up lookups by unique bill invoice number
CREATE INDEX IF NOT EXISTS idx_bills_bill_number 
    ON bills (bill_number);


-- =============================================================================
-- INDEXES ON BILL ITEMS
-- =============================================================================
-- Speeds up fetching line items when rendering or printing a single bill
CREATE INDEX IF NOT EXISTS idx_bill_items_bill_id 
    ON bill_items (bill_id);


-- =============================================================================
-- INDEXES ON PAYMENTS & AUDIT
-- =============================================================================
-- Speeds up finding all payments recorded against a given bill
CREATE INDEX IF NOT EXISTS idx_payments_bill_id 
    ON payments (bill_id);

-- Speeds up lookup by transaction/receipt reference
CREATE INDEX IF NOT EXISTS idx_payments_reference 
    ON payments (payment_reference);

-- Speeds up finding active successful payments vs cancelled
CREATE INDEX IF NOT EXISTS idx_payments_status 
    ON payments (payment_status);

-- Speeds up finding payment audit trail records
CREATE INDEX IF NOT EXISTS idx_payment_reversals_payment_id 
    ON payment_reversals (payment_id);

CREATE INDEX IF NOT EXISTS idx_payment_reversals_bill_id 
    ON payment_reversals (bill_id);
