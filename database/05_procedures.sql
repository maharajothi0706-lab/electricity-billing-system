/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 05: STORED PROCEDURES (PL/pgSQL)
================================================================================
  Purpose:
    Implements complex business transactions via PostgreSQL Stored Procedures:
    1. sp_generate_monthly_bill: Computes and inserts bill + bill_items atomically.
    2. sp_record_payment: Safely records a payment with row-level concurrency locking.
    3. sp_reverse_payment: Cancels a payment with full audit trail logging.

  Academic / Viva Note:
    - PostgreSQL 11+ supports CREATE PROCEDURE with CALL syntax.
    - Unlike FUNCTIONS which must return a value and are evaluated as part of
      expressions, PROCEDURES can commit and rollback transactions internally
      and manage state transitions.
    - We use SELECT ... FOR UPDATE within procedures to achieve Pessimistic
      Concurrency Control, preventing the classic "Lost Update" or "Overpayment"
      race condition when two cashiers process payments simultaneously.
================================================================================
*/

-- =============================================================================
-- PROCEDURE 1: sp_generate_monthly_bill
-- =============================================================================
/*
  Requirement 14.C:
  Procedure to generate a monthly bill using an accepted meter reading.
  
  Transaction Flow:
    1. Lock and validate the target meter reading.
    2. Ensure reading has not already been billed.
    3. Retrieve the consumer's active tariff schedule.
    4. Calculate progressive slab charges and fixed charges.
    5. Generate unique bill invoice number.
    6. Insert new record into BILLS table.
    7. Insert itemized breakdown records into BILL_ITEMS table.
    8. Mark METER_READINGS.is_billed as TRUE.
*/
CREATE OR REPLACE PROCEDURE sp_generate_monthly_bill(
    p_reading_id INT,
    p_due_days INT DEFAULT 15,
    INOUT p_bill_id INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_reading RECORD;
    v_consumer RECORD;
    v_tariff RECORD;
    v_slab RECORD;
    v_bill_number VARCHAR(30);
    v_energy_charge NUMERIC(10, 2) := 0.00;
    v_fixed_charge NUMERIC(10, 2) := 0.00;
    v_tax_amount NUMERIC(10, 2) := 0.00;
    v_total_amount NUMERIC(10, 2) := 0.00;
    v_due_date DATE;
BEGIN
    -- Step 1: Validate meter reading exists and lock row
    SELECT * INTO v_reading
    FROM meter_readings
    WHERE reading_id = p_reading_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Meter reading ID % not found.', p_reading_id;
    END IF;

    IF v_reading.is_billed = TRUE THEN
        RAISE EXCEPTION 'Meter reading ID % has already been billed.', p_reading_id;
    END IF;

    -- Step 2: Fetch consumer details
    SELECT * INTO v_consumer
    FROM consumers
    WHERE consumer_id = v_reading.consumer_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consumer ID % not found for reading %.', v_reading.consumer_id, p_reading_id;
    END IF;

    -- Step 3: Fetch active tariff plan matching consumer connection type
    SELECT * INTO v_tariff
    FROM tariffs
    WHERE connection_type = v_consumer.connection_type
      AND is_active = TRUE
      AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
    ORDER BY effective_from DESC
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active tariff configuration found for connection type "%".', v_consumer.connection_type;
    END IF;

    -- Step 4: Fixed standing charge from tariff
    v_fixed_charge := v_tariff.fixed_charge;

    -- Step 5: Generate unique invoice number
    v_bill_number := fn_generate_bill_number(v_reading.reading_month);
    v_due_date := CURRENT_DATE + (p_due_days || ' days')::INTERVAL;

    -- Step 6: Insert draft bill to obtain new bill_id
    INSERT INTO bills (
        bill_number,
        consumer_id,
        meter_reading_id,
        billing_period,
        units_consumed,
        energy_charge,
        fixed_charge,
        tax_amount,
        total_amount,
        amount_paid,
        outstanding_amount,
        bill_date,
        due_date,
        payment_status
    ) VALUES (
        v_bill_number,
        v_consumer.consumer_id,
        v_reading.reading_id,
        v_reading.reading_month,
        v_reading.units_consumed,
        0.00,
        v_fixed_charge,
        0.00,
        v_fixed_charge,
        0.00,
        v_fixed_charge,
        CURRENT_DATE,
        v_due_date,
        'UNPAID'
    )
    RETURNING bill_id INTO p_bill_id;

    -- Step 7: Calculate progressive slab charges and insert bill items
    FOR v_slab IN 
        SELECT * FROM fn_calculate_progressive_slabs(v_tariff.tariff_id, v_reading.units_consumed)
    LOOP
        v_energy_charge := v_energy_charge + v_slab.slab_charge;

        INSERT INTO bill_items (
            bill_id,
            item_type,
            description,
            units,
            rate,
            amount
        ) VALUES (
            p_bill_id,
            'SLAB_CHARGE',
            v_slab.description || ' (' || v_slab.units_in_slab || ' units @ ₹' || v_slab.rate || ')',
            v_slab.units_in_slab,
            v_slab.rate,
            v_slab.slab_charge
        );
    END LOOP;

    -- Step 8: Insert fixed charge line item
    INSERT INTO bill_items (
        bill_id,
        item_type,
        description,
        units,
        rate,
        amount
    ) VALUES (
        p_bill_id,
        'FIXED_CHARGE',
        'Monthly Standing Meter Rent & Maintenance Charge',
        0.00,
        0.00,
        v_fixed_charge
    );

    -- Step 9: Compute Electricity Duty / Tax (5% on energy charge for Commercial/Industrial, 0% for Domestic under 100 units)
    IF v_consumer.connection_type IN ('COMMERCIAL', 'INDUSTRIAL') OR v_reading.units_consumed > 100 THEN
        v_tax_amount := ROUND((v_energy_charge * 0.05), 2);
        
        INSERT INTO bill_items (
            bill_id,
            item_type,
            description,
            units,
            rate,
            amount
        ) VALUES (
            p_bill_id,
            'TAX',
            'Electricity Duty & Regulatory Surcharge (5%)',
            0.00,
            5.00,
            v_tax_amount
        );
    ELSE
        v_tax_amount := 0.00;
    END IF;

    -- Step 10: Calculate total bill amount and update header
    v_total_amount := v_energy_charge + v_fixed_charge + v_tax_amount;

    UPDATE bills
    SET energy_charge = v_energy_charge,
        tax_amount = v_tax_amount,
        total_amount = v_total_amount,
        outstanding_amount = v_total_amount
    WHERE bill_id = p_bill_id;

    -- Step 11: Mark meter reading as billed
    UPDATE meter_readings
    SET is_billed = TRUE
    WHERE reading_id = p_reading_id;

END;
$$;

COMMENT ON PROCEDURE sp_generate_monthly_bill(INT, INT, INOUT INT) IS 
'Generates an electricity bill from a meter reading with itemized progressive tariff slabs in an ACID transaction.';


-- =============================================================================
-- PROCEDURE 2: sp_record_payment
-- =============================================================================
/*
  Records a payment against a bill using Pessimistic Row Locking (FOR UPDATE).
  Prevents overpayments and race conditions.
*/
CREATE OR REPLACE PROCEDURE sp_record_payment(
    p_bill_id INT,
    p_amount NUMERIC,
    p_method VARCHAR,
    p_remarks TEXT,
    p_recorded_by VARCHAR,
    INOUT p_payment_id INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_bill RECORD;
    v_ref VARCHAR(50);
BEGIN
    -- Validate payment amount is positive
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Payment amount (%) must be greater than zero.', p_amount;
    END IF;

    -- Lock bill row for update to prevent concurrent overpayments
    SELECT * INTO v_bill
    FROM bills
    WHERE bill_id = p_bill_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Bill ID % does not exist.', p_bill_id;
    END IF;

    IF v_bill.payment_status = 'PAID' OR v_bill.outstanding_amount <= 0 THEN
        RAISE EXCEPTION 'Bill % is already fully paid. No balance outstanding.', v_bill.bill_number;
    END IF;

    -- Prevent overpayment beyond outstanding balance
    IF p_amount > v_bill.outstanding_amount THEN
        RAISE EXCEPTION 'Payment amount (₹%) exceeds the current outstanding balance (₹%).', 
            p_amount, v_bill.outstanding_amount;
    END IF;

    -- Generate reference receipt code
    v_ref := fn_generate_payment_reference();

    -- Insert payment transaction record
    INSERT INTO payments (
        bill_id,
        payment_reference,
        payment_date,
        amount_paid,
        payment_method,
        payment_status,
        remarks,
        recorded_by
    ) VALUES (
        p_bill_id,
        v_ref,
        CURRENT_TIMESTAMP,
        p_amount,
        p_method,
        'SUCCESS',
        p_remarks,
        p_recorded_by
    )
    RETURNING payment_id INTO p_payment_id;

    -- Trigger trg_update_bill_payment_status will automatically update bills table!
END;
$$;

COMMENT ON PROCEDURE sp_record_payment(INT, NUMERIC, VARCHAR, TEXT, VARCHAR, INOUT INT) IS 
'Records a consumer payment with row-level locking to guarantee no concurrent overpayments occur.';


-- =============================================================================
-- PROCEDURE 3: sp_reverse_payment
-- =============================================================================
/*
  Reverses / cancels a payment transaction while maintaining an immutable audit log.
*/
CREATE OR REPLACE PROCEDURE sp_reverse_payment(
    p_payment_id INT,
    p_reason TEXT,
    p_reversed_by VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_payment RECORD;
BEGIN
    -- Lock payment record
    SELECT * INTO v_payment
    FROM payments
    WHERE payment_id = p_payment_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Payment ID % does not exist.', p_payment_id;
    END IF;

    IF v_payment.payment_status = 'CANCELLED' THEN
        RAISE EXCEPTION 'Payment ID % has already been reversed / cancelled.', p_payment_id;
    END IF;

    -- Mark payment as CANCELLED
    UPDATE payments
    SET payment_status = 'CANCELLED'
    WHERE payment_id = p_payment_id;

    -- Insert audit log entry
    INSERT INTO payment_reversals (
        payment_id,
        bill_id,
        reversal_reason,
        reversed_amount,
        reversed_at,
        reversed_by
    ) VALUES (
        p_payment_id,
        v_payment.bill_id,
        p_reason,
        v_payment.amount_paid,
        CURRENT_TIMESTAMP,
        p_reversed_by
    );

    -- Trigger trg_update_bill_payment_status will re-evaluate bills outstanding balance!
END;
$$;

COMMENT ON PROCEDURE sp_reverse_payment(INT, TEXT, VARCHAR) IS 
'Reverses a payment transaction and inserts an audit log entry while keeping the original record intact.';
