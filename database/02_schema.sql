/*
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  SCRIPT 02: RELATIONAL SCHEMA DEFINITION (DDL)
================================================================================
  Purpose:
    Defines all foundational relational tables conforming to Third Normal Form
    (3NF) with explicit primary keys, foreign keys, not-null constraints,
    default values, check constraints, and descriptive PostgreSQL catalog comments.

  Entity Relationships Overview:
    1. USERS: System operators and administrators managing the utility.
    2. CONSUMERS: Citizens or commercial establishments receiving power supply.
    3. TARIFFS: Master tariff policy headers per consumer connection type.
    4. TARIFF_SLABS: Configurable progressive rate slabs belonging to a tariff.
    5. METER_READINGS: Monthly meter consumption logs for each consumer.
    6. BILLS: Invoices calculated progressively from meter readings.
    7. BILL_ITEMS: Snapshot breakdown of each progressive tariff slab applied.
    8. PAYMENTS: Ledger of collections made against generated bills.
    9. PAYMENT_REVERSALS: Audit trail of reversed / cancelled payment transactions.
================================================================================
*/

-- =============================================================================
-- TABLE 1: USERS (Authentication and Role-Based Access Control)
-- =============================================================================
/*
  The USERS table stores credentials for system administrators and billing operators.
  Passwords are stored as cryptographic hashes (bcrypt/PBKDF2 via Werkzeug),
  never in plaintext, satisfying security guidelines.
*/
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'OPERATOR',
    email VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- CHECK constraint to restrict user roles to predefined valid types
    CONSTRAINT chk_user_role CHECK (role IN ('ADMIN', 'OPERATOR'))
);

COMMENT ON TABLE users IS 'Stores administrative and operational staff credentials with secure password hashes.';
COMMENT ON COLUMN users.user_id IS 'Auto-incrementing surrogate primary key for internal user tracking.';
COMMENT ON COLUMN users.username IS 'Unique login identifier for the application.';
COMMENT ON COLUMN users.role IS 'User permission level: ADMIN has full access; OPERATOR handles billing and payments.';


-- =============================================================================
-- TABLE 2: CONSUMERS (Master Entity for Electricity Customers)
-- =============================================================================
/*
  The CONSUMERS table stores customer profile information, physical address,
  meter identification, and account status.
  
  Normalization Note:
  - 1NF: Every attribute holds atomic values.
  - 2NF: No partial dependency on primary key (single-column PK consumer_id).
  - 3NF: No transitive dependencies; attributes depend strictly on consumer_id.
*/
CREATE TABLE IF NOT EXISTS consumers (
    consumer_id SERIAL PRIMARY KEY,
    consumer_number VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(50) NOT NULL DEFAULT 'Metropolis',
    phone_number VARCHAR(15) NOT NULL,
    email VARCHAR(100) NOT NULL,
    meter_number VARCHAR(30) UNIQUE NOT NULL,
    connection_type VARCHAR(20) NOT NULL DEFAULT 'DOMESTIC',
    connection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    account_status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Business constraint: Connection category must be one of three utility types
    CONSTRAINT chk_consumer_connection_type CHECK (connection_type IN ('DOMESTIC', 'COMMERCIAL', 'INDUSTRIAL')),
    
    -- Business constraint: Account status can only be ACTIVE or INACTIVE
    CONSTRAINT chk_consumer_status CHECK (account_status IN ('ACTIVE', 'INACTIVE'))
);

COMMENT ON TABLE consumers IS 'Master table containing profile and meter association for registered electricity consumers.';
COMMENT ON COLUMN consumers.consumer_id IS 'Primary key uniquely identifying each consumer entity.';
COMMENT ON COLUMN consumers.consumer_number IS 'Human-readable unique alphanumeric reference number (e.g., CONS-1001).';
COMMENT ON COLUMN consumers.meter_number IS 'Unique hardware identifier assigned to the physical electricity meter.';
COMMENT ON COLUMN consumers.account_status IS 'Flag indicating active connection or deactivation (soft delete).';


-- =============================================================================
-- TABLE 3: TARIFFS (Tariff Master Header)
-- =============================================================================
/*
  Stores overall tariff policy metadata for each connection type, including the
  mandatory fixed monthly standing charge and policy validity period.
*/
CREATE TABLE IF NOT EXISTS tariffs (
    tariff_id SERIAL PRIMARY KEY,
    tariff_name VARCHAR(60) NOT NULL,
    connection_type VARCHAR(20) NOT NULL,
    fixed_charge NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_tariff_connection_type CHECK (connection_type IN ('DOMESTIC', 'COMMERCIAL', 'INDUSTRIAL')),
    CONSTRAINT chk_tariff_fixed_charge CHECK (fixed_charge >= 0.00)
);

COMMENT ON TABLE tariffs IS 'Master catalog of electricity pricing policies and fixed standing charges.';
COMMENT ON COLUMN tariffs.tariff_id IS 'Primary key for tariff rate structure.';
COMMENT ON COLUMN tariffs.fixed_charge IS 'Fixed monthly maintenance/meter rent fee added to every bill.';


-- =============================================================================
-- TABLE 4: TARIFF_SLABS (Progressive Consumption Slabs)
-- =============================================================================
/*
  Stores progressive tiered slabs for dynamic bill computation.
  Example:
    Slab 1: 0 to 100 units at ₹2.00/unit
    Slab 2: 101 to 200 units at ₹3.00/unit
    Slab 3: Above 200 units (NULL max_units) at ₹5.00/unit
*/
CREATE TABLE IF NOT EXISTS tariff_slabs (
    slab_id SERIAL PRIMARY KEY,
    tariff_id INT NOT NULL REFERENCES tariffs(tariff_id) ON DELETE CASCADE,
    slab_number INT NOT NULL,
    min_units NUMERIC(10, 2) NOT NULL,
    max_units NUMERIC(10, 2), -- NULL denotes unbounded upper limit (e.g., '> 200 units')
    rate_per_unit NUMERIC(10, 2) NOT NULL,
    slab_description VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Sane numerical bounds
    CONSTRAINT chk_slab_min_units CHECK (min_units >= 0),
    CONSTRAINT chk_slab_max_units CHECK (max_units IS NULL OR max_units > min_units),
    CONSTRAINT chk_slab_rate CHECK (rate_per_unit >= 0),
    CONSTRAINT uq_tariff_slab UNIQUE (tariff_id, slab_number)
);

COMMENT ON TABLE tariff_slabs IS 'Tiered consumption brackets and respective unit rates per tariff plan.';
COMMENT ON COLUMN tariff_slabs.slab_number IS 'Sequential slab order index (1, 2, 3, etc.).';
COMMENT ON COLUMN tariff_slabs.max_units IS 'Upper ceiling of this bracket; NULL indicates infinite / above threshold.';


-- =============================================================================
-- TABLE 5: METER_READINGS (Monthly Consumption Data)
-- =============================================================================
/*
  Stores monthly meter readings taken by field meter inspectors.
  Enforces relational integrity via foreign key to consumers table.
  Units consumed is derived: current_reading - previous_reading.
*/
CREATE TABLE IF NOT EXISTS meter_readings (
    reading_id SERIAL PRIMARY KEY,
    consumer_id INT NOT NULL REFERENCES consumers(consumer_id) ON DELETE RESTRICT,
    reading_month VARCHAR(7) NOT NULL, -- Stored as ISO format 'YYYY-MM'
    previous_reading NUMERIC(10, 2) NOT NULL,
    current_reading NUMERIC(10, 2) NOT NULL,
    units_consumed NUMERIC(10, 2) NOT NULL,
    reading_date DATE NOT NULL DEFAULT CURRENT_DATE,
    reading_remarks TEXT,
    is_billed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: Negative readings are physically impossible
    CONSTRAINT chk_reading_non_negative CHECK (previous_reading >= 0 AND current_reading >= 0),
    
    -- Constraint: Current reading cannot be less than previous reading
    CONSTRAINT chk_reading_logical_flow CHECK (current_reading >= previous_reading),
    
    -- Constraint: Units consumed must match the arithmetic difference
    CONSTRAINT chk_units_consumed_math CHECK (units_consumed = (current_reading - previous_reading)),
    
    -- Constraint: Exactly one accepted meter reading per consumer per billing month
    CONSTRAINT uq_consumer_reading_month UNIQUE (consumer_id, reading_month)
);

COMMENT ON TABLE meter_readings IS 'Monthly physical meter measurements used for billing consumption.';
COMMENT ON COLUMN meter_readings.reading_month IS 'Billing period cycle in YYYY-MM format (e.g. 2026-10).';
COMMENT ON COLUMN meter_readings.is_billed IS 'Boolean flag indicating whether a bill has been generated for this reading.';


-- =============================================================================
-- TABLE 6: BILLS (Electricity Invoices)
-- =============================================================================
/*
  Represents generated consumer bills for a billing cycle.
  
  Academic Note on Intentional Historical Denormalization:
  - Energy charge, fixed charge, and tax are stored directly on the bill row
    as an immutable financial snapshot. If tariff rates change in the future,
    past bills MUST remain unchanged. This aligns with financial auditing rules.
*/
CREATE TABLE IF NOT EXISTS bills (
    bill_id SERIAL PRIMARY KEY,
    bill_number VARCHAR(30) UNIQUE NOT NULL,
    consumer_id INT NOT NULL REFERENCES consumers(consumer_id) ON DELETE RESTRICT,
    meter_reading_id INT UNIQUE NOT NULL REFERENCES meter_readings(reading_id) ON DELETE RESTRICT,
    billing_period VARCHAR(7) NOT NULL,
    units_consumed NUMERIC(10, 2) NOT NULL,
    energy_charge NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    fixed_charge NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(10, 2) NOT NULL,
    amount_paid NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    outstanding_amount NUMERIC(10, 2) NOT NULL,
    bill_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Arithmetic validity checks
    CONSTRAINT chk_bill_amounts_positive CHECK (
        energy_charge >= 0 AND 
        fixed_charge >= 0 AND 
        tax_amount >= 0 AND 
        total_amount >= 0 AND 
        amount_paid >= 0 AND 
        outstanding_amount >= 0
    ),
    -- Total must equal sum of its constituent components
    CONSTRAINT chk_bill_total_sum CHECK (total_amount = (energy_charge + fixed_charge + tax_amount)),
    
    -- Outstanding balance equation
    CONSTRAINT chk_bill_outstanding_math CHECK (outstanding_amount = (total_amount - amount_paid)),
    
    -- Allowed lifecycle statuses
    CONSTRAINT chk_bill_payment_status CHECK (payment_status IN ('UNPAID', 'PARTIALLY PAID', 'PAID'))
);

COMMENT ON TABLE bills IS 'Monthly electricity bills generated from validated meter readings.';
COMMENT ON COLUMN bills.bill_number IS 'Human-readable unique invoice reference (e.g., BILL-2026-10-001).';
COMMENT ON COLUMN bills.outstanding_amount IS 'Remaining balance owed by consumer (total_amount - amount_paid).';
COMMENT ON COLUMN bills.payment_status IS 'Current settlement status: UNPAID, PARTIALLY PAID, or PAID.';


-- =============================================================================
-- TABLE 7: BILL_ITEMS (Slab-by-Slab Calculation Audit)
-- =============================================================================
/*
  Itemized breakdown of how the energy charge and standing charges were computed.
  This allows printing a comprehensive line-item invoice for the consumer.
*/
CREATE TABLE IF NOT EXISTS bill_items (
    item_id SERIAL PRIMARY KEY,
    bill_id INT NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
    item_type VARCHAR(30) NOT NULL,
    description VARCHAR(150) NOT NULL,
    units NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    rate NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_bill_item_amount CHECK (amount >= 0),
    CONSTRAINT chk_bill_item_type CHECK (item_type IN ('SLAB_CHARGE', 'FIXED_CHARGE', 'TAX', 'ADJUSTMENT'))
);

COMMENT ON TABLE bill_items IS 'Line item details explaining the progressive slab charge breakdown of each bill.';


-- =============================================================================
-- TABLE 8: PAYMENTS (Collections Ledger)
-- =============================================================================
/*
  Stores all payments made by consumers against issued bills.
  Partial payments are supported.
  Payments can be reversed, but are never deleted, ensuring financial integrity.
*/
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    bill_id INT NOT NULL REFERENCES bills(bill_id) ON DELETE RESTRICT,
    payment_reference VARCHAR(50) UNIQUE NOT NULL,
    payment_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount_paid NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    remarks TEXT,
    recorded_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_payment_amount_positive CHECK (amount_paid > 0.00),
    CONSTRAINT chk_payment_method CHECK (payment_method IN ('CASH', 'UPI', 'BANK_TRANSFER', 'DEBIT_CARD', 'NET_BANKING', 'CHEQUE')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('SUCCESS', 'CANCELLED'))
);

COMMENT ON TABLE payments IS 'Financial transactions recording consumer bill payments.';
COMMENT ON COLUMN payments.payment_reference IS 'Unique receipt or banking transaction reference.';
COMMENT ON COLUMN payments.payment_status IS 'Transaction status: SUCCESS or CANCELLED (via audit reversal).';


-- =============================================================================
-- TABLE 9: PAYMENT_REVERSALS (Audit Trail for Reversed Payments)
-- =============================================================================
/*
  Maintains an immutable audit log of any cancelled or reversed payment records,
  complying with financial audit and accounting standards.
*/
CREATE TABLE IF NOT EXISTS payment_reversals (
    reversal_id SERIAL PRIMARY KEY,
    payment_id INT NOT NULL REFERENCES payments(payment_id) ON DELETE RESTRICT,
    bill_id INT NOT NULL REFERENCES bills(bill_id) ON DELETE RESTRICT,
    reversal_reason TEXT NOT NULL,
    reversed_amount NUMERIC(10, 2) NOT NULL,
    reversed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reversed_by VARCHAR(50) NOT NULL,

    CONSTRAINT chk_reversal_amount CHECK (reversed_amount > 0.00)
);

COMMENT ON TABLE payment_reversals IS 'Immutable audit trail capturing all payment cancellations and reasons.';
