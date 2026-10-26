# Entity-Relationship (ER) Diagram & Schema Specifications

## Electricity Billing and Consumption Management System

### 1. Conceptual ER Diagram (Mermaid)

```mermaid
erDiagram
    USERS ||--o{ BILLS : records_or_audits
    CONSUMERS ||--o{ METER_READINGS : submits
    CONSUMERS ||--o{ BILLS : billed_to
    TARIFFS ||--|{ TARIFF_SLABS : configures
    METER_READINGS ||--|| BILLS : evaluated_into
    BILLS ||--|{ BILL_ITEMS : broken_down_into
    BILLS ||--o{ PAYMENTS : settled_by
    PAYMENTS ||--o{ PAYMENT_REVERSALS : audited_by

    CONSUMERS {
        int consumer_id PK "Surrogate Primary Key"
        varchar consumer_number UK "Unique Alphanumeric (CONS-XXXX)"
        varchar full_name "Customer Name"
        text address "Physical Service Address"
        varchar city "Distribution Jurisdiction"
        varchar phone_number "Contact Telephone"
        varchar email "Customer Email"
        varchar meter_number UK "Unique Hardware Serial (MTR-XXXX)"
        varchar connection_type "DOMESTIC | COMMERCIAL | INDUSTRIAL"
        date connection_date "Sanction Date"
        varchar account_status "ACTIVE | INACTIVE"
        timestamptz created_at "Registration Timestamp"
    }

    TARIFFS {
        int tariff_id PK "Primary Key"
        varchar tariff_name "Policy Schedule Name"
        varchar connection_type "Target Category"
        numeric fixed_charge "Monthly Standing Charge"
        date effective_from "Start Date"
        date effective_to "End Date (or NULL)"
        boolean is_active "Active Policy Flag"
        timestamptz created_at "Creation Timestamp"
    }

    TARIFF_SLABS {
        int slab_id PK "Primary Key"
        int tariff_id FK "References tariffs(tariff_id)"
        int slab_number "Sequential Slab Index (1, 2, 3)"
        numeric min_units "Bracket Lower Bound (kWh)"
        numeric max_units "Bracket Upper Bound (kWh or NULL)"
        numeric rate_per_unit "Rate per kWh (₹)"
        varchar slab_description "Description Label"
        timestamptz created_at "Creation Timestamp"
    }

    METER_READINGS {
        int reading_id PK "Primary Key"
        int consumer_id FK "References consumers(consumer_id)"
        varchar reading_month "Cycle Period (YYYY-MM)"
        numeric previous_reading "Start Dial Reading (kWh)"
        numeric current_reading "End Dial Reading (kWh)"
        numeric units_consumed "Computed Usage (kWh)"
        date reading_date "Inspection Date"
        text reading_remarks "Field Observations"
        boolean is_billed "Invoice Generated Flag"
        timestamptz created_at "Recorded Timestamp"
    }

    BILLS {
        int bill_id PK "Primary Key"
        varchar bill_number UK "Unique Invoice Code (BILL-YYYYMM-XXXX)"
        int consumer_id FK "References consumers(consumer_id)"
        int meter_reading_id FK "Unique References meter_readings(reading_id)"
        varchar billing_period "Cycle Period (YYYY-MM)"
        numeric units_consumed "Billed Energy (kWh)"
        numeric energy_charge "Progressive Slab Total (₹)"
        numeric fixed_charge "Standing Monthly Charge (₹)"
        numeric tax_amount "Electricity Duty 5% (₹)"
        numeric total_amount "Total Invoice Sum (₹)"
        numeric amount_paid "Total Settled (₹)"
        numeric outstanding_amount "Remaining Balance (₹)"
        date bill_date "Issue Date"
        date due_date "Payment Deadline"
        varchar payment_status "PAID | PARTIALLY PAID | UNPAID"
        timestamptz created_at "Generation Timestamp"
    }

    BILL_ITEMS {
        int item_id PK "Primary Key"
        int bill_id FK "References bills(bill_id)"
        varchar item_type "SLAB_CHARGE | FIXED_CHARGE | TAX"
        varchar description "Line Item Narrative"
        numeric units "Units applied in this slab"
        numeric rate "Unit Rate (₹/kWh)"
        numeric amount "Line Item Charge (₹)"
        timestamptz created_at "Creation Timestamp"
    }

    PAYMENTS {
        int payment_id PK "Primary Key"
        int bill_id FK "References bills(bill_id)"
        varchar payment_reference UK "Receipt Reference (RCPT-YYYYMMDD-XXXX)"
        timestamptz payment_date "Transaction Timestamp"
        numeric amount_paid "Settled Amount (₹)"
        varchar payment_method "CASH | UPI | BANK_TRANSFER | NET_BANKING | DEBIT_CARD"
        varchar payment_status "SUCCESS | CANCELLED"
        text remarks "Transaction Notes"
        varchar recorded_by "Cashier / System User"
        timestamptz created_at "Recorded Timestamp"
    }

    PAYMENT_REVERSALS {
        int reversal_id PK "Primary Key"
        int payment_id FK "References payments(payment_id)"
        int bill_id FK "References bills(bill_id)"
        text reversal_reason "Audited Justification"
        numeric reversed_amount "Amount Cancelled (₹)"
        timestamptz reversed_at "Audit Timestamp"
        varchar reversed_by "Authorizing Admin"
    }

    USERS {
        int user_id PK "Primary Key"
        varchar username UK "Unique Login ID"
        varchar password_hash "Cryptographic Salted Hash"
        varchar full_name "Staff Name"
        varchar role "ADMIN | OPERATOR"
        varchar email UK "Official Email"
        boolean is_active "Active Account Flag"
        timestamptz created_at "Creation Timestamp"
    }
```

---

### 2. Relationship Cardinalities

| Relationship | Entities Involved | Cardinality | Explanation |
| :--- | :--- | :--- | :--- |
| **Consumer to Meter Readings** | `consumers` $\rightarrow$ `meter_readings` | $1 : N$ (One-to-Many) | One consumer receives multiple monthly meter readings over time. A unique constraint ensures exactly one reading per consumer per billing cycle. |
| **Meter Reading to Bill** | `meter_readings` $\rightarrow$ `bills` | $1 : 1$ (One-to-One) | Each meter reading generates exactly one bill invoice via a UNIQUE foreign key constraint. |
| **Tariff to Slabs** | `tariffs` $\rightarrow$ `tariff_slabs` | $1 : N$ (One-to-Many) | One tariff schedule contains multiple progressive consumption tier slabs (e.g. 0-100, 100-200, >200 units). |
| **Bill to Bill Items** | `bills` $\rightarrow$ `bill_items` | $1 : N$ (One-to-Many) | Each bill is broken down into itemized line entries preserving the progressive slab charges, fixed charges, and taxes. |
| **Bill to Payments** | `bills` $\rightarrow$ `payments` | $1 : N$ (One-to-Many) | Consumers may settle a bill via a single lump sum or multiple partial installment payments. |
| **Payment to Reversal** | `payments` $\rightarrow$ `payment_reversals` | $1 : 1$ (One-to-One audit) | A cancelled payment has at most one reversal entry documenting the cancellation reason. |
