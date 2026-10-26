"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  BILLING SERVICE MODULE
================================================================================
  Handles electricity consumption math, progressive tariff slab evaluation,
  and invoice generation logic.
"""

from decimal import Decimal, ROUND_HALF_UP
from database.db import execute_query, execute_query_one, execute_dml, get_db_connection

def calculate_units_consumed(previous_reading, current_reading):
    """
    Validates readings and computes units consumed.
    Raises ValueError if readings are negative or current < previous.
    """
    prev = Decimal(str(previous_reading))
    curr = Decimal(str(current_reading))

    if prev < 0:
        raise ValueError("Previous meter reading cannot be negative.")
    if curr < 0:
        raise ValueError("Current meter reading cannot be negative.")
    if curr < prev:
        raise ValueError(f"Current reading ({curr}) cannot be lower than previous reading ({prev}).")

    return curr - prev

def calculate_slab_breakdown(tariff_id, units):
    """
    Computes progressive tiered slab charges for a given consumption volume.
    Returns: (list_of_slab_items, total_energy_charge)
    
    Example: 250 units with Domestic Tariff (0-100 @ 2, 100-200 @ 3, >200 @ 5):
      Slab 1: 100 * 2 = 200
      Slab 2: 100 * 3 = 300
      Slab 3: 50 * 5 = 250
      Total = 750
    """
    units_dec = Decimal(str(units))
    if units_dec <= 0:
        return [], Decimal("0.00")

    slabs = execute_query(
        """
        SELECT slab_number, min_units, max_units, rate_per_unit, slab_description
        FROM tariff_slabs
        WHERE tariff_id = %s
        ORDER BY slab_number ASC
        """,
        (tariff_id,)
    )

    breakdown = []
    total_energy_charge = Decimal("0.00")
    remaining_units = units_dec

    for slab in slabs:
        min_u = Decimal(str(slab["min_units"]))
        max_u = Decimal(str(slab["max_units"])) if slab["max_units"] is not None else None
        rate = Decimal(str(slab["rate_per_unit"]))
        desc = slab["slab_description"] or f"Slab {slab['slab_number']}"

        if max_u is not None:
            capacity = max_u - min_u
            applicable = min(remaining_units, capacity)
        else:
            applicable = remaining_units

        if applicable > 0:
            charge = (applicable * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_energy_charge += charge
            breakdown.append({
                "slab_number": slab["slab_number"],
                "description": desc,
                "units": float(applicable),
                "rate": float(rate),
                "amount": float(charge)
            })
            remaining_units -= applicable

        if remaining_units <= 0:
            break

    return breakdown, total_energy_charge

def generate_bill_for_reading(reading_id, due_days=15):
    """
    Generates a formal bill from an accepted meter reading within an ACID transaction.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch and lock reading
            cur.execute(
                """
                SELECT mr.*, c.connection_type, c.consumer_number, c.full_name
                FROM meter_readings mr
                JOIN consumers c ON mr.consumer_id = c.consumer_id
                WHERE mr.reading_id = %s
                FOR UPDATE
                """,
                (reading_id,)
            )
            reading = cur.fetchone()
            if not reading:
                raise ValueError(f"Reading ID {reading_id} not found.")

            # Unpack columns
            r_id, c_id, r_month, prev_r, curr_r, units, r_date, r_rem, is_billed, created_at, conn_type, c_num, c_name = reading

            if is_billed:
                raise ValueError(f"Reading for {r_month} has already been billed.")

            # 2. Check if active tariff exists
            cur.execute(
                """
                SELECT tariff_id, tariff_name, fixed_charge
                FROM tariffs
                WHERE connection_type = %s AND is_active = TRUE
                ORDER BY effective_from DESC LIMIT 1
                """,
                (conn_type,)
            )
            tariff = cur.fetchone()
            if not tariff:
                raise ValueError(f"No active tariff configured for connection type '{conn_type}'.")

            t_id, t_name, fixed_charge = tariff
            fixed_charge = Decimal(str(fixed_charge))

            # 3. Progressive slab calculation
            units_dec = Decimal(str(units))
            breakdown, energy_charge = calculate_slab_breakdown(t_id, units_dec)

            # 4. Tax / Duty calculation (5% for Commercial/Industrial or Domestic > 100 units)
            if conn_type in ("COMMERCIAL", "INDUSTRIAL") or units_dec > 100:
                tax_amount = (energy_charge * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                tax_amount = Decimal("0.00")

            total_amount = energy_charge + fixed_charge + tax_amount
            outstanding_amount = total_amount

            # 5. Generate bill number
            cur.execute(
                "SELECT COUNT(*) + 1 FROM bills WHERE billing_period = %s",
                (r_month,)
            )
            seq = cur.fetchone()[0]
            clean_period = r_month.replace("-", "")
            bill_number = f"BILL-{clean_period}-{seq:04d}"

            # 6. Insert into bills
            cur.execute(
                """
                INSERT INTO bills (
                    bill_number, consumer_id, meter_reading_id, billing_period,
                    units_consumed, energy_charge, fixed_charge, tax_amount,
                    total_amount, amount_paid, outstanding_amount, bill_date,
                    due_date, payment_status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.00, %s, CURRENT_DATE,
                    CURRENT_DATE + (%s || ' days')::INTERVAL, 'UNPAID'
                ) RETURNING bill_id
                """,
                (bill_number, c_id, r_id, r_month, units_dec, energy_charge, fixed_charge, tax_amount, total_amount, outstanding_amount, str(due_days))
            )
            new_bill_id = cur.fetchone()[0]

            # 7. Insert line items into bill_items
            for item in breakdown:
                cur.execute(
                    """
                    INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount)
                    VALUES (%s, 'SLAB_CHARGE', %s, %s, %s, %s)
                    """,
                    (new_bill_id, f"{item['description']} ({item['units']} units @ ₹{item['rate']})", item['units'], item['rate'], item['amount'])
                )

            # Fixed charge item
            cur.execute(
                """
                INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount)
                VALUES (%s, 'FIXED_CHARGE', 'Monthly Standing Meter Rent & Maintenance Charge', 0, 0, %s)
                """,
                (new_bill_id, fixed_charge)
            )

            # Tax item if applicable
            if tax_amount > 0:
                cur.execute(
                    """
                    INSERT INTO bill_items (bill_id, item_type, description, units, rate, amount)
                    VALUES (%s, 'TAX', 'Electricity Duty & Regulatory Surcharge (5%)', 0, 5.0, %s)
                    """,
                    (new_bill_id, tax_amount)
                )

            # 8. Mark reading as billed
            cur.execute("UPDATE meter_readings SET is_billed = TRUE WHERE reading_id = %s", (r_id,))

            return new_bill_id

def batch_generate_bills_for_period(billing_period):
    """
    Generates bills for all unbilled readings in a specific billing period.
    Returns: (generated_count, failed_count, errors_list)
    """
    readings = execute_query(
        """
        SELECT reading_id, consumer_id, reading_month
        FROM meter_readings
        WHERE reading_month = %s AND is_billed = FALSE
        ORDER BY reading_id ASC
        """,
        (billing_period,)
    )

    generated = 0
    failed = 0
    errors = []

    for r in readings:
        try:
            generate_bill_for_reading(r["reading_id"])
            generated += 1
        except Exception as e:
            failed += 1
            errors.append(f"Reading ID {r['reading_id']} (Consumer {r['consumer_id']}): {str(e)}")

    return generated, failed, errors
