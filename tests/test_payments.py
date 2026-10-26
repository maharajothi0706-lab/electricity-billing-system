"""
================================================================================
  DBMS MINI PROJECT: ELECTRICITY BILLING AND CONSUMPTION MANAGEMENT SYSTEM
  PAYMENT PROCESSING & STATUS TRANSITION UNIT TESTS
================================================================================
"""

import pytest
from decimal import Decimal

def simulate_payment_update(bill_total, existing_payments, new_payment_amount):
    """Simulates payment arithmetic and status transitions matching DB trigger."""
    total = Decimal(str(bill_total))
    current_paid = sum(Decimal(str(p)) for p in existing_payments)
    outstanding = total - current_paid
    new_pay = Decimal(str(new_payment_amount))

    # Reject non-positive amounts
    if new_pay <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    # Reject overpayment
    if new_pay > outstanding:
        raise ValueError(f"Payment amount (₹{new_pay}) exceeds outstanding balance (₹{outstanding}).")

    updated_paid = current_paid + new_pay
    updated_outstanding = total - updated_paid

    if updated_paid >= total:
        status = "PAID"
    elif updated_paid > 0:
        status = "PARTIALLY PAID"
    else:
        status = "UNPAID"

    return updated_paid, updated_outstanding, status

def test_full_payment_updates_status_to_paid():
    """Requirement 19.8 & 19.10: Record full payment and update status to PAID."""
    paid, outstanding, status = simulate_payment_update(
        bill_total=1000.00,
        existing_payments=[],
        new_payment_amount=1000.00
    )
    assert paid == Decimal("1000.00")
    assert outstanding == Decimal("0.00")
    assert status == "PAID"

def test_partial_payment_updates_status_to_partially_paid():
    """Requirement 19.8 & 19.10: Record partial payment and update status to PARTIALLY PAID."""
    paid, outstanding, status = simulate_payment_update(
        bill_total=1000.00,
        existing_payments=[],
        new_payment_amount=400.00
    )
    assert paid == Decimal("400.00")
    assert outstanding == Decimal("600.00")
    assert status == "PARTIALLY PAID"

def test_subsequent_partial_payment_completes_bill():
    """Requirement 19.11: Subsequent payment settling remaining balance."""
    paid, outstanding, status = simulate_payment_update(
        bill_total=1000.00,
        existing_payments=[400.00],
        new_payment_amount=600.00
    )
    assert paid == Decimal("1000.00")
    assert outstanding == Decimal("0.00")
    assert status == "PAID"

def test_reject_zero_or_negative_payment():
    """Requirement 19.9: Reject payment amounts <= 0."""
    with pytest.raises(ValueError, match="greater than zero"):
        simulate_payment_update(
            bill_total=500.00,
            existing_payments=[],
            new_payment_amount=0.00
        )

    with pytest.raises(ValueError, match="greater than zero"):
        simulate_payment_update(
            bill_total=500.00,
            existing_payments=[],
            new_payment_amount=-50.00
        )

def test_reject_overpayment_beyond_balance():
    """Requirement 19.9: Reject payment amounts exceeding outstanding amount."""
    with pytest.raises(ValueError, match="exceeds outstanding balance"):
        simulate_payment_update(
            bill_total=500.00,
            existing_payments=[200.00],  # 300 remaining
            new_payment_amount=350.00   # tries to pay 350
        )
