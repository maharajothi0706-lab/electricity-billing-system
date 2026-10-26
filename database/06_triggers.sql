/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 06: DATABASE TRIGGERS (PL/pgSQL)
================================================================================
  Purpose:
    Enforces business integrity constraints and real-time synchronization
    automatically at the database engine level via event triggers:
    1. trg_validate_meter_reading: Validates meter inputs BEFORE INSERT/UPDATE.
    2. trg_update_bill_payment_status: Recalculates bill balances AFTER payment events.
    3. trg_prevent_duplicate_bill: Guard against generating multiple bills per reading.

  Academic / Viva Note:
    - A Trigger is a specialized stored procedure that executes automatically
      in response to certain events (INSERT, UPDATE, DELETE) on a table.
    - BEFORE triggers are used to inspect, modify, or reject rows before they
      are written to disk (validation & data transformation).
    - AFTER triggers are used to cascade updates or maintain denormalized
      aggregates across related tables (e.g., updating bill balances after payment).
    - The special variables NEW and OLD represent the new row being inserted/updated
      and the existing row being modified/deleted, respectively.
================================================================================
*/

-- =============================================================================
-- TRIGGER 1: trg_validate_meter_reading
-- =============================================================================
/*
  Requirement 14.D:
  Trigger to prevent invalid or duplicate readings and ensure mathematical integrity.
  
  Actions:
    - Validates that consumer is ACTIVE.
    - Validates previous and current readings.
    - Automatically sets units_consumed = (current_reading - previous_reading).
    - Checks that current reading is >= previous reading.
*/
CREATE OR REPLACE FUNCTION fn_trg_validate_meter_reading()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR(10);
BEGIN
    -- Check 1: Ensure consumer is ACTIVE
    SELECT account_status INTO v_status
    FROM consumers
    WHERE consumer_id = NEW.consumer_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Consumer ID % does not exist.', NEW.consumer_id;
    END IF;

    IF v_status = 'INACTIVE' THEN
        RAISE EXCEPTION 'Cannot record meter readings for an INACTIVE consumer (ID %).', NEW.consumer_id;
    END IF;

    -- Check 2: Reject negative meter readings
    IF NEW.previous_reading < 0 THEN
        RAISE EXCEPTION 'Previous reading cannot be negative (provided: %).', NEW.previous_reading;
    END IF;

    IF NEW.current_reading < 0 THEN
        RAISE EXCEPTION 'Current reading cannot be negative (provided: %).', NEW.current_reading;
    END IF;

    -- Check 3: Current reading cannot be less than previous reading
    IF NEW.current_reading < NEW.previous_reading THEN
        RAISE EXCEPTION 'Current reading (%) cannot be lower than previous reading (%). Physical meter roll-back is invalid.',
            NEW.current_reading, NEW.previous_reading;
    END IF;

    -- Automatically compute units consumed to guarantee mathematical consistency
    NEW.units_consumed := NEW.current_reading - NEW.previous_reading;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_meter_reading ON meter_readings;
CREATE TRIGGER trg_validate_meter_reading
    BEFORE INSERT OR UPDATE ON meter_readings
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_validate_meter_reading();

COMMENT ON TRIGGER trg_validate_meter_reading ON meter_readings IS 
'Validates reading sanity and auto-calculates units_consumed before saving to disk.';


-- =============================================================================
-- TRIGGER 2: trg_update_bill_payment_status
-- =============================================================================
/*
  Requirement 14.E:
  Trigger to keep bill payment status consistent with successful payment records.
  Fires AFTER INSERT OR UPDATE on payments table.
  
  Actions:
    - Calculates the total sum of all SUCCESSFUL payments recorded for the bill.
    - Deducts this sum from total_amount to compute outstanding_amount.
    - Automatically transitions payment_status to 'PAID', 'PARTIALLY PAID', or 'UNPAID'.
*/
CREATE OR REPLACE FUNCTION fn_trg_update_bill_payment_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_bill_id INT;
    v_total_paid NUMERIC(10, 2);
    v_total_amount NUMERIC(10, 2);
    v_outstanding NUMERIC(10, 2);
    v_status VARCHAR(20);
BEGIN
    -- Determine which bill was impacted
    IF TG_OP = 'DELETE' THEN
        v_target_bill_id := OLD.bill_id;
    ELSE
        v_target_bill_id := NEW.bill_id;
    END IF;

    -- Fetch the invoice total amount
    SELECT total_amount INTO v_total_amount
    FROM bills
    WHERE bill_id = v_target_bill_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Aggregate only successful payments (ignoring CANCELLED ones)
    SELECT COALESCE(SUM(amount_paid), 0.00) INTO v_total_paid
    FROM payments
    WHERE bill_id = v_target_bill_id
      AND payment_status = 'SUCCESS';

    -- Compute remaining balance
    v_outstanding := GREATEST(0.00, v_total_amount - v_total_paid);

    -- Determine status label
    IF v_total_paid >= v_total_amount THEN
        v_status := 'PAID';
        v_outstanding := 0.00;
    ELSIF v_total_paid > 0.00 THEN
        v_status := 'PARTIALLY PAID';
    ELSE
        v_status := 'UNPAID';
    END IF;

    -- Update parent bill record
    UPDATE bills
    SET amount_paid = v_total_paid,
        outstanding_amount = v_outstanding,
        payment_status = v_status
    WHERE bill_id = v_target_bill_id;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_bill_payment_status ON payments;
CREATE TRIGGER trg_update_bill_payment_status
    AFTER INSERT OR UPDATE OR DELETE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_update_bill_payment_status();

COMMENT ON TRIGGER trg_update_bill_payment_status ON payments IS 
'Maintains real-time synchronization of bill outstanding amounts and payment statuses.';
