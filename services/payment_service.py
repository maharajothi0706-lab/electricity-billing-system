"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  PAYMENT SERVICE MODULE
================================================================================
  Handles payment collections, partial settlements, concurrency locking,
  and reversible audit trails.
"""

from decimal import Decimal
from datetime import datetime
from database.db import get_db_connection, execute_query, execute_query_one

def record_bill_payment(bill_id, amount, payment_method, remarks="", recorded_by="system"):
    """
    Records a payment against a bill using Pessimistic Row-Level Locking (FOR UPDATE)
    to protect against concurrent double-payments and overpayments.
    """
    amount_dec = Decimal(str(amount))
    if amount_dec <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    valid_methods = ('CASH', 'UPI', 'BANK_TRANSFER', 'DEBIT_CARD', 'NET_BANKING', 'CHEQUE')
    if payment_method not in valid_methods:
        raise ValueError(f"Invalid payment method '{payment_method}'. Must be one of {valid_methods}.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Row-level lock on the bill
            cur.execute(
                """
                SELECT bill_id, bill_number, total_amount, amount_paid, outstanding_amount, payment_status
                FROM bills
                WHERE bill_id = %s
                FOR UPDATE
                """,
                (bill_id,)
            )
            bill = cur.fetchone()
            if not bill:
                raise ValueError(f"Bill ID {bill_id} not found.")

            b_id, b_num, total_amt, amt_paid, outstanding, status = bill
            total_amt = Decimal(str(total_amt))
            amt_paid = Decimal(str(amt_paid))
            outstanding = Decimal(str(outstanding))

            if status == 'PAID' or outstanding <= 0:
                raise ValueError(f"Bill {b_num} is already fully paid. Outstanding balance is ₹0.00.")

            if amount_dec > outstanding:
                raise ValueError(
                    f"Payment amount of ₹{amount_dec:.2f} exceeds outstanding balance of ₹{outstanding:.2f}."
                )

            # 2. Generate unique reference code
            today_str = datetime.now().strftime("%Y%m%d")
            cur.execute(
                "SELECT COUNT(*) + 1 FROM payments WHERE DATE(payment_date) = CURRENT_DATE"
            )
            seq = cur.fetchone()[0]
            ref_number = f"RCPT-{today_str}-{seq:04d}"

            # 3. Insert payment record
            cur.execute(
                """
                INSERT INTO payments (
                    bill_id, payment_reference, payment_date, amount_paid,
                    payment_method, payment_status, remarks, recorded_by
                ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, 'SUCCESS', %s, %s)
                RETURNING payment_id
                """,
                (b_id, ref_number, amount_dec, payment_method, remarks, recorded_by)
            )
            payment_id = cur.fetchone()[0]

            # 4. Trigger trg_update_bill_payment_status will update the bill automatically.
            # Explicit update as fallback:
            new_paid = amt_paid + amount_dec
            new_outstanding = max(Decimal("0.00"), total_amt - new_paid)
            new_status = 'PAID' if new_outstanding == 0 else 'PARTIALLY PAID'

            cur.execute(
                """
                UPDATE bills
                SET amount_paid = %s,
                    outstanding_amount = %s,
                    payment_status = %s
                WHERE bill_id = %s
                """,
                (new_paid, new_outstanding, new_status, b_id)
            )

            return {
                "payment_id": payment_id,
                "payment_reference": ref_number,
                "bill_number": b_num,
                "amount_paid": float(amount_dec),
                "outstanding_remaining": float(new_outstanding),
                "new_status": new_status
            }

def reverse_payment(payment_id, reversal_reason, reversed_by="admin"):
    """
    Cancels / reverses a previously recorded payment and creates an audit trail record.
    The original payment record is preserved with status 'CANCELLED'.
    """
    if not reversal_reason or len(reversal_reason.strip()) < 5:
        raise ValueError("A clear, valid reversal reason of at least 5 characters is required.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Lock payment row
            cur.execute(
                """
                SELECT payment_id, bill_id, amount_paid, payment_status, payment_reference
                FROM payments
                WHERE payment_id = %s
                FOR UPDATE
                """,
                (payment_id,)
            )
            payment = cur.fetchone()
            if not payment:
                raise ValueError(f"Payment ID {payment_id} does not exist.")

            p_id, b_id, amount_paid, p_status, p_ref = payment
            amount_paid = Decimal(str(amount_paid))

            if p_status == 'CANCELLED':
                raise ValueError(f"Payment {p_ref} is already cancelled/reversed.")

            # 2. Mark payment CANCELLED
            cur.execute(
                "UPDATE payments SET payment_status = 'CANCELLED' WHERE payment_id = %s",
                (p_id,)
            )

            # 3. Insert audit log
            cur.execute(
                """
                INSERT INTO payment_reversals (
                    payment_id, bill_id, reversal_reason, reversed_amount, reversed_at, reversed_by
                ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                RETURNING reversal_id
                """,
                (p_id, b_id, reversal_reason, amount_paid, reversed_by)
            )
            reversal_id = cur.fetchone()[0]

            # 4. Re-calculate bill totals from all active SUCCESS payments
            cur.execute(
                """
                SELECT COALESCE(SUM(amount_paid), 0.00)
                FROM payments
                WHERE bill_id = %s AND payment_status = 'SUCCESS'
                """,
                (b_id,)
            )
            active_paid = Decimal(str(cur.fetchone()[0]))

            cur.execute("SELECT total_amount FROM bills WHERE bill_id = %s", (b_id,))
            total_amt = Decimal(str(cur.fetchone()[0]))

            new_outstanding = max(Decimal("0.00"), total_amt - active_paid)
            if active_paid >= total_amt:
                new_status = 'PAID'
            elif active_paid > 0:
                new_status = 'PARTIALLY PAID'
            else:
                new_status = 'UNPAID'

            cur.execute(
                """
                UPDATE bills
                SET amount_paid = %s,
                    outstanding_amount = %s,
                    payment_status = %s
                WHERE bill_id = %s
                """,
                (active_paid, new_outstanding, new_status, b_id)
            )

            return {
                "reversal_id": reversal_id,
                "payment_id": p_id,
                "reversed_amount": float(amount_paid),
                "new_bill_outstanding": float(new_outstanding),
                "new_bill_status": new_status
            }
