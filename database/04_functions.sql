/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 04: STORED FUNCTIONS (PL/pgSQL)
================================================================================
  Purpose:
    Encapsulates core business logic inside the PostgreSQL database engine:
    1. fn_calculate_units_consumed: Validates and computes meter usage units.
    2. fn_calculate_progressive_slabs: Evaluates tiered slab rates progressively.
    3. fn_get_latest_reading: Finds the most recent reading for a consumer.
    4. fn_generate_bill_number: Generates formatted unique invoice identifiers.
    5. fn_generate_payment_reference: Generates unique receipt references.

  Academic / Viva Note:
    - PL/pgSQL (Procedural Language / PostgreSQL) allows procedural structures
      such as IF-THEN-ELSE, LOOPS, and EXCEPTION blocks inside SQL.
    - Executing calculations inside the database minimizes network latency
      and guarantees consistent business rules regardless of client software.
================================================================================
*/

-- =============================================================================
-- FUNCTION 1: fn_calculate_units_consumed
-- =============================================================================
/*
  Requirement 14.B:
  Function to calculate units consumed from two valid readings.
  Validates that readings are non-negative and current reading is >= previous.
*/
CREATE OR REPLACE FUNCTION fn_calculate_units_consumed(
    p_previous_reading NUMERIC,
    p_current_reading NUMERIC
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE -- Deterministic: Always produces the exact same output for the same inputs
AS $$
BEGIN
    -- Business rule: Readings cannot be negative
    IF p_previous_reading < 0 THEN
        RAISE EXCEPTION 'Previous reading (%) cannot be negative.', p_previous_reading;
    END IF;

    IF p_current_reading < 0 THEN
        RAISE EXCEPTION 'Current reading (%) cannot be negative.', p_current_reading;
    END IF;

    -- Business rule: Current reading cannot be less than previous reading
    IF p_current_reading < p_previous_reading THEN
        RAISE EXCEPTION 'Current reading (%) is lower than previous reading (%). Meter rollover requires explicit administrative authorization.', 
            p_current_reading, p_previous_reading;
    END IF;

    -- Calculate consumption
    RETURN (p_current_reading - p_previous_reading);
END;
$$;

COMMENT ON FUNCTION fn_calculate_units_consumed(NUMERIC, NUMERIC) IS 
'Computes electricity consumption units with strict non-negative and logical sequence validation.';


-- =============================================================================
-- FUNCTION 2: fn_calculate_progressive_slabs
-- =============================================================================
/*
  Requirement 14.A:
  Function to calculate progressive slab-based energy charges.
  
  Progressive Slab Calculation Logic Example:
    Suppose consumption is 250 units under Domestic Tariff:
      - Slab 1 (0 to 100): 100 units * ₹2.00 = ₹200.00
      - Slab 2 (101 to 200): 100 units * ₹3.00 = ₹300.00
      - Slab 3 (> 200): 50 units * ₹5.00 = ₹250.00
      - Energy Charge Subtotal = 200 + 300 + 250 = ₹750.00
      - Fixed Standing Charge = ₹100.00
      - Total Bill = ₹850.00
*/
CREATE OR REPLACE FUNCTION fn_calculate_progressive_slabs(
    p_tariff_id INT,
    p_units NUMERIC
)
RETURNS TABLE (
    slab_num INT,
    description VARCHAR,
    units_in_slab NUMERIC,
    rate NUMERIC,
    slab_charge NUMERIC
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    r RECORD;
    v_remaining_units NUMERIC := p_units;
    v_slab_capacity NUMERIC;
    v_applicable_units NUMERIC;
    v_charge NUMERIC;
BEGIN
    -- If consumption is 0, return no slab charges
    IF p_units <= 0 THEN
        RETURN;
    END IF;

    -- Iterate through configured slabs ordered sequentially by slab_number
    FOR r IN 
        SELECT 
            ts.slab_number,
            ts.min_units,
            ts.max_units,
            ts.rate_per_unit,
            ts.slab_description
        FROM tariff_slabs ts
        WHERE ts.tariff_id = p_tariff_id
        ORDER BY ts.slab_number ASC
    LOOP
        -- Determine maximum capacity of this slab
        IF r.max_units IS NOT NULL THEN
            v_slab_capacity := r.max_units - r.min_units;
            -- How many units fall within this slab?
            v_applicable_units := LEAST(v_remaining_units, v_slab_capacity);
        ELSE
            -- Unbounded upper slab: all remaining units fall here
            v_applicable_units := v_remaining_units;
        END IF;

        IF v_applicable_units > 0 THEN
            v_charge := ROUND(v_applicable_units * r.rate_per_unit, 2);
            
            slab_num := r.slab_number;
            description := COALESCE(r.slab_description, 'Slab ' || r.slab_number);
            units_in_slab := v_applicable_units;
            rate := r.rate_per_unit;
            slab_charge := v_charge;

            RETURN NEXT;

            v_remaining_units := v_remaining_units - v_applicable_units;
        END IF;

        -- Break loop early if all units have been consumed across previous slabs
        EXIT WHEN v_remaining_units <= 0;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION fn_calculate_progressive_slabs(INT, NUMERIC) IS 
'Returns itemized progressive tiered slab charge calculations for a given consumption volume.';


-- =============================================================================
-- FUNCTION 3: fn_get_latest_reading
-- =============================================================================
/*
  Finds the most recent accepted meter reading for a consumer.
  Used when a meter reader prepares to record a new monthly reading.
*/
CREATE OR REPLACE FUNCTION fn_get_latest_reading(p_consumer_id INT)
RETURNS NUMERIC
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_last_reading NUMERIC;
BEGIN
    SELECT current_reading INTO v_last_reading
    FROM meter_readings
    WHERE consumer_id = p_consumer_id
    ORDER BY reading_month DESC, reading_date DESC
    LIMIT 1;

    -- If no previous readings exist, initial default reading is 0
    RETURN COALESCE(v_last_reading, 0.00);
END;
$$;

COMMENT ON FUNCTION fn_get_latest_reading(INT) IS 
'Retrieves the most recent meter reading value for auto-populating next previous_reading.';


-- =============================================================================
-- FUNCTION 4: fn_generate_bill_number
-- =============================================================================
/*
  Generates a clean, human-readable invoice identifier.
  Format: BILL-YYYYMM-XXXX (e.g., BILL-202610-0001)
*/
CREATE OR REPLACE FUNCTION fn_generate_bill_number(p_billing_period VARCHAR)
RETURNS VARCHAR
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
    v_clean_period VARCHAR := REPLACE(p_billing_period, '-', '');
    v_count INT;
    v_new_number VARCHAR;
BEGIN
    SELECT COUNT(*) + 1 INTO v_count
    FROM bills
    WHERE billing_period = p_billing_period;

    v_new_number := 'BILL-' || v_clean_period || '-' || LPAD(v_count::TEXT, 4, '0');
    RETURN v_new_number;
END;
$$;

COMMENT ON FUNCTION fn_generate_bill_number(VARCHAR) IS 
'Generates formatted unique bill invoice number based on billing month sequence.';


-- =============================================================================
-- FUNCTION 5: fn_generate_payment_reference
-- =============================================================================
/*
  Generates a unique payment receipt reference.
  Format: RCPT-YYYYMMDD-XXXX
*/
CREATE OR REPLACE FUNCTION fn_generate_payment_reference()
RETURNS VARCHAR
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
    v_date_str VARCHAR := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
    v_count INT;
BEGIN
    SELECT COUNT(*) + 1 INTO v_count
    FROM payments
    WHERE DATE(payment_date) = CURRENT_DATE;

    RETURN 'RCPT-' || v_date_str || '-' || LPAD(v_count::TEXT, 4, '0');
END;
$$;

COMMENT ON FUNCTION fn_generate_payment_reference() IS 
'Generates standardized unique payment transaction reference number.';
