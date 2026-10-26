/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 10: RESET / RE-INITIALIZATION SCRIPT (DEVELOPMENT & TESTING ONLY)
================================================================================
  Purpose:
    Safely tears down all application views, triggers, procedures, functions,
    and tables in correct reverse-dependency order.
    
  Academic / Safety Note:
    - Never run this script against a live production database.
    - Dropping tables with CASCADE automatically removes dependent foreign keys,
      views, and triggers, but cleaning up explicitly ensures zero leftover artifacts.
================================================================================
*/

-- Step 1: Drop Views
DROP VIEW IF EXISTS v_unpaid_bills CASCADE;
DROP VIEW IF EXISTS v_top_consumers CASCADE;
DROP VIEW IF EXISTS v_revenue_by_month CASCADE;
DROP VIEW IF EXISTS monthly_consumption_summary CASCADE;
DROP VIEW IF EXISTS consumer_billing_summary CASCADE;

-- Step 2: Drop Triggers and Trigger Functions
DROP TRIGGER IF EXISTS trg_validate_meter_reading ON meter_readings CASCADE;
DROP FUNCTION IF EXISTS fn_trg_validate_meter_reading() CASCADE;

DROP TRIGGER IF EXISTS trg_update_bill_payment_status ON payments CASCADE;
DROP FUNCTION IF EXISTS fn_trg_update_bill_payment_status() CASCADE;

-- Step 3: Drop Stored Procedures
DROP PROCEDURE IF EXISTS sp_generate_monthly_bill(INT, INT, INT) CASCADE;
DROP PROCEDURE IF EXISTS sp_record_payment(INT, NUMERIC, VARCHAR, TEXT, VARCHAR, INT) CASCADE;
DROP PROCEDURE IF EXISTS sp_reverse_payment(INT, TEXT, VARCHAR) CASCADE;

-- Step 4: Drop Functions
DROP FUNCTION IF EXISTS fn_calculate_units_consumed(NUMERIC, NUMERIC) CASCADE;
DROP FUNCTION IF EXISTS fn_calculate_progressive_slabs(INT, NUMERIC) CASCADE;
DROP FUNCTION IF EXISTS fn_get_latest_reading(INT) CASCADE;
DROP FUNCTION IF EXISTS fn_generate_bill_number(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS fn_generate_payment_reference() CASCADE;

-- Step 5: Drop Tables (in reverse foreign key dependency order)
DROP TABLE IF EXISTS payment_reversals CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS bill_items CASCADE;
DROP TABLE IF EXISTS bills CASCADE;
DROP TABLE IF EXISTS meter_readings CASCADE;
DROP TABLE IF EXISTS tariff_slabs CASCADE;
DROP TABLE IF EXISTS tariffs CASCADE;
DROP TABLE IF EXISTS consumers CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Confirmation output
SELECT 'Database schema reset completed successfully. You may now run scripts 02 through 08.' AS status;
